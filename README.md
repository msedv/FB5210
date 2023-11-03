# Long story short

Wir haben eine Gasheizung von Windhager, zwei Heizkreise, jeweils ein "Windhager MES Bedienmodul FB 5210". Alles bei uns ist in unserem internen IoT - außer der Windhager. Seit Jahren suche ich nach einer passenden Lösung, um zumindest lesend auf die Daten der Heizung zugreifen zu können. Drei Ansätze scheint es dabei zu geben:

a. ein Webserver-Modul von Windhager, das aber teuer ist und in die Heizung eingebaut werden muss
b. Zugriff auf den LON-Bus an der Heizung, siehe z.B. <https://www.g3gg0.de/wordpress/esp32/mes-wifi-bringing-a-windhager-pellet-heater-online/>
c. Zugriff auf die Kommunikation zwischen den Bedienmodulen und der Heizungszentrale

Die dritte Variante hat mir schon immer recht gut gefallen, da damit der Eingriff ins System minimal ist; bereits 2019 hat der User Mischak unter <https://www.haustechnikdialog.de/Forum/t/99932/Welcher-Bus-bei-FB-5210-Windhager> die Rahmenparameter dazu gepostet:
# Interface Windhager MES Bedienmodul FB 5210

Zwischen Bedienmodulen und Heizungszentrale wird eine 2-Draht-Schnittstelle mit 10-12V Spannung verwendet auf der tatsächlich nur ein RS232-Protokoll mit 4800 Baud und 8N1 gefahren wird. Der Zugriff ist trivial: Spannungsteiler mit z.B. 15/39k (siehe <https://www.aeq-web.com/spannungsteiler-microcontroller-berechnen-und-dimensionieren/>) oder gleich einen Optokoppler um auf Mikrocontroller-taugliche 3-3,3V zu kommen, dann:

1. mit RS232-TTL-USB-Wandler an einen Raspberry Pi oder
2. ESP8288 mit tasmota-zbbridge.bin (siehe <https://tasmota.github.io/docs/Serial-to-TCP-Bridge/>) eine "Serial to TCP Bridge" bauen

# ESP8266 Serial to TCP Bridge

Ich habe zwei (da zwei Heizkreise und zwei Regler!) der ESPs genommen, mit tasmota-zbbridge.bin geflasht, dann:
```
	TCPBaudRate 4800
	TCPStart 10000
```
Das TCPStart muss man nach jedem Boot von Hand machen; alternativ gleich ein Regel definieren, die das automatisch macht:
```
	Rule1 ON System#Boot do TCPStart 10000 endon
	Rule1 1
```
Im ersten Versuch habe ich die Pins Serial RX/TX (hardware RS232) verwendet, was bei mir **nicht** funktioniert hat, also stattdessen D1/D2 - und diese als TCP Rx/TCP Tx wobei in meinem Testaufbau Tx **nicht** angeschlossen ist sondern nur RX - wäre ja schon mal froh wenn das Lesen funktionieren würde:

![TasmotConfigZbBridge](https://github.com/msedv/FB5210/assets/7942032/230c6de5-a642-4e17-982d-0c81dc156cbb)

# Protokoll

Nach TCPStart 10000 kann man sich via Port 10000 mit den ESPs verbinden und bekommt die Daten des Busses relativ schön angezeigt. Haken: der erwähnte User Mischak hat zwar 2019 unter <https://www.haustechnikdialog.de/Forum/t/99932/Welcher-Bus-bei-FB-5210-Windhager> ein paar Brotkrumen hinterlassen, unter <https://github.com/mischak/fb5210> ein Github-Repository und auch großspurig angekündigt, dass seine Schnittstelle "fast fertig" sei nur mehr etwas "Kosmetik" bedürfe - nur, seit 2019 nichts mehr, auch sämtliche Anfragen im Forum etc. von anderen Usern nach dem Stand der Dinge blieben unbeantwortet.
Was ich bis jetzt aus seinem Posting und meinen Experimenten herausgefunden habe:
* binäres Protokoll, Pakete werden durch \x10\x02 (Start) und \x10\x03 (Ende) begrenzt
* kommt ein \x10 im Datenstrom vor so wird es als \x10\x10 escaped
* Temperaturen scheinen nach dem Schema "(255.0 * byte1 + byte2) / 100" in zwei Byte codiert zu sein; \x7fff steht für "kein Wert". Also \x091a = 32,21°

# Testprogramm

test.py ist ein Q&D Python3-Programm, das sich zu einem ESP connected, die Pakete filtert, den CRC-Wert überprüft (macht Sinn - ein paar Prozent der Pakete fallen durch!) und versucht die eine oder andere Temperatur anzuzeigen - bis jetzt gelingt mir das bestenfalls für ein paar Werte, z.B.:

```
034619000d6811d37fff 8.35 63.75 34.19 45.46 - 
03467fff15097fff7fff 8.35 - 53.64 - -
```
Siehe Source.

# Testdaten

Ebenfalls im Repository zwei Testdumps meiner beiden Heizkreise; so sieht man ein sortierte Liste der Pakete ohne Dupikate:
```
grep -v "\*\*\*\|Ungültiger\|Starte" dump1.txt | sort -u
grep -v "\*\*\*\|Ungültiger\|Starte" dump2.txt | sort -u
```
Was ich recht gerne mache ist auch zu checken was in beiden Protokollen an identischen Daten vorhanden ist:

```
comm -12 <( grep -v "\*\*\*\|Ungültiger\|Starte" dump1.txt | sort -u ) <( grep -v "\*\*\*\|Ungültiger\|Starte" dump2.txt | sort -u )
```
Das ergibt beispielsweise für die beiden Dumps:
```
91007f030203050400
91007f030203050e00
92007f03026708020402646401
92007f03026708020433646401
92007f03026708020434646401
92007f03026708020441646401
92007f03026708020442646401
92007f03026708020443646401
92007f03026708020450646401
92007f0302670803050202646400
92007f0302670803053333646400
92007f0302670803053434646400
92007f0302670803054141646400
92007f0302670803054242646400
92007f0302670803054343646400
92007f0302670803055050646401
92007f030277070400
92007f030277070e00
92057f030277072100 ASK_RAUM
9b7f050283e700
```
# Conclusio

Also, wer auch immer etwas beitragen kann - **bitte** her damit! :-)
