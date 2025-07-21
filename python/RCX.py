

#Red-Crawl-Mother
import subprocess

# Der Reddit-Crawler liefert Treffer für Aktiensymbole und speichert die durchsuchten Posts
subprocess.run(['python', r"C:\Users\IHR-PFAD\Reddit-Crawler\Skripte\RC01-Crawler.py"])

# Das Skript erstellt aus den gefundenen Aktiensymbolen eine tabellarische Übersicht
subprocess.run(['python', r"C:\Users\IHR-PFAD\Reddit-Crawler\Skripte\RC02-Tabelle.py"])
print ('RC02-Tabelle.py erfolgreich')

# Das Skript identifiziert die Aktien, die gerade eine steigende Popularität verzeichnen
subprocess.run(['python', r"C:\Users\IHR-PFAD\Reddit-Crawler\Skripte\RC03-Hotleads.py"])
print ('RC03-Hotleads.py erfolgreich')

# Das Skript erstellt einzelne Posts-Dateien für die Aktie, zu denen ein Post existiert
subprocess.run(['python', r"C:\Users\IHR-PFAD\Reddit-Crawler\Skripte\RC04-Hotleads-Postfilter.py"])
print ('RC04-Hotleads-Postfilter.py erfolgreich')

# Die Gemini-KI analysiert die Posts-Dateien und erstellt ein Dokument "Gesamtanalyse" 
subprocess.run(['python', r"C:\Users\IHR-PFAD\Reddit-Crawler\Skripte\RC05-Hotleads-KI-Analyse.py"])
print ('RC05-Hotleads-KI-Analyse.py erfolgreich')

# Hochzeit der Dokumente Hotleads.docx und Gesamtanalyse.docx
subprocess.run(['python', r"C:\Users\IHR-PFAD\Reddit-Crawler\Skripte\RC06-Report.py"])
print ('RC06-Report.py erfolgreich')


