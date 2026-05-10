"""
Skript na pridanie 500 slovenských tréningových emailov do databázy.
Spusti: python add_slovak_data.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spam_filter.db")

SLOVAK_EMAILS = [
    # ══════════════════════════════════════════════════════
    #  SPAM (1) — 250 emailov
    # ══════════════════════════════════════════════════════

    # Výhry a lotérie
    ("Gratulujeme! Vyhrali ste 500 000 EUR! Kliknite sem a získajte svoju výhru!", 1),
    ("Ste víťazom našej lotérie! Vaša cena čaká. Kontaktujte nás ihneď!", 1),
    ("VÝHRA! Váš e-mail bol vyžrebovaný. Získajte 100 000 EUR ešte dnes!", 1),
    ("Blahoželáme! Vyhrali ste luxusné auto. Potvrďte svoju adresu teraz!", 1),
    ("Ste naším šťastným výhercom týždňa! Cena: 250 000 EUR. Konajte hneď!", 1),
    ("Vaše telefónne číslo vyhralo hlavnú cenu v lotérii. Zavolajte nám!", 1),
    ("ŠPECIÁLNA VÝHRA: iPhone 15 Pro zadarmo! Len pre vás. Kliknite tu!", 1),
    ("Získajte svoju výhru 1 000 000 EUR. Stačí kliknúť a potvrdiť totožnosť!", 1),
    ("Vyhrali ste dovolenku na Maledivách! Rezervujte si miesto ešte dnes!", 1),
    ("Lotéria EuroMillions: Váš lístok vyhral! Nárokujte si výhru do 48 hodín!", 1),

    # Finančné podvody
    ("Zarobte 5000 EUR týždenne z pohodlia domova! Bez skúseností. Začnite hneď!", 1),
    ("Tajná metóda zarábania online. 10 000 EUR mesačne garantovaných!", 1),
    ("Investujte 100 EUR a získajte 10 000 EUR za mesiac. 100% istota!", 1),
    ("Kryptomena BOOM! Investujte teraz a zdvojnásobte peniaze za 24 hodín!", 1),
    ("Exkluzívna investičná príležitosť. Návratnosť 500%. Obmedzený počet miest!", 1),
    ("Rýchla pôžička bez dokladovania príjmu! Schválenie do 10 minút!", 1),
    ("Máte dlhy? Pomôžeme vám! Pôžička 50 000 EUR bez záruky. Volajte teraz!", 1),
    ("Zarobte na forexe bez skúseností! Náš robot zarába za vás 24/7!", 1),
    ("Binárne opcie: Zarobte 1000 EUR denne. Registrujte sa zadarmo!", 1),
    ("Nigérijský princ potrebuje vašu pomoc. Odmena 10% z 5 miliónov USD!", 1),
    ("Prevod dedičstva vo výške 2 milióny EUR. Potrebujeme vašu spoluprácu!", 1),
    ("Získajte grant EÚ 15 000 EUR. Žiadne splácanie. Požiadajte ešte dnes!", 1),
    ("Pracujte z domu a zarobte 3000 EUR mesačne! Žiadne skúsenosti potrebné!", 1),
    ("MLM príležitosť! Zarobte budovaním siete. Pasívny príjem navždy!", 1),
    ("Predávajte naše produkty online a zarobte 500 EUR denne!", 1),

    # Phishing a bezpečnostné hrozby
    ("URGENT: Váš bankový účet bol zablokovaný. Prihláste sa ihneď!", 1),
    ("Upozornenie: Podozrivá aktivita na vašom účte. Overte totožnosť teraz!", 1),
    ("Váš PayPal účet bude zrušený. Kliknite sem na overenie do 24 hodín!", 1),
    ("Slovenská sporiteľňa: Váš účet bol kompromitovaný. Konajte okamžite!", 1),
    ("VÚB Banka: Neautorizovaná transakcia 899 EUR. Potvrďte alebo zrušte!", 1),
    ("Tatra banka: Váš internetbanking bol zablokovaný. Obnovte prístup tu!", 1),
    ("Apple ID: Váš účet bol použitý v cudzej krajine. Zabezpečte ho hneď!", 1),
    ("Google: Niekto sa prihlásil do vášho účtu z Číny. Zmeňte heslo ihneď!", 1),
    ("Facebook: Váš profil bude vymazaný. Potvrdením predídete zrušeniu!", 1),
    ("DHL: Váš balík čaká. Zaplaťte poplatok 2,99 EUR za doručenie.", 1),
    ("Slovenská pošta: Balík zadržaný na colnici. Uhraďte 4,50 EUR online.", 1),
    ("Finančná správa SR: Máte nedoplatok dane. Zaplaťte do 48 hodín!", 1),
    ("Polícia SR: Bol zaznamenaný pokus o podvod z vášho počítača. Konajte!", 1),
    ("Microsoft: Váš počítač má vírus. Zavolajte technickú podporu ihneď!", 1),
    ("AKTUALIZÁCIA ÚČTU: Potvrďte svoje údaje alebo stratíte prístup!", 1),

    # Zdravie a lieky
    ("Schudnite 10 kg za 2 týždne! Zázračná tabletka. Bez diéty a cvičenia!", 1),
    ("Viagra a Cialis online bez predpisu! Diskrétne doručenie domov!", 1),
    ("Prírodný liek na cukrovku. Lekári nechcú, aby ste to vedeli!", 1),
    ("Zväčšite svoju mužnosť o 10 cm za 30 dní. Garantované výsledky!", 1),
    ("Detox na 7 dní. Stratíte 5 kg a vyčistíte telo od toxínov!", 1),
    ("Liečba rakoviny prírodnou cestou. Farmaceutické firmy to skrývajú!", 1),
    ("Zázračný krém na vrásky. Vyzerajte o 20 rokov mladšie za týždeň!", 1),
    ("Anaboliká a steroidy online. Rýchly svalový rast. Diskrétne!", 1),
    ("Lieky na úzkosť a depresiu bez predpisu. Objednajte online!", 1),
    ("Prírodný liek na vysoký tlak. Zabudnite na tabletky navždy!", 1),

    # Erotika a zoznamovanie
    ("Slobodné ženy vo vašom meste čakajú na vás! Registrujte sa zadarmo!", 1),
    ("Horúce rande dnes večer! Tisíce žien hľadajú partnera vo vašom okolí!", 1),
    ("Tajné stretnutia pre ženatých. 100% diskrétnosť zaručená!", 1),
    ("Dospelý obsah ZADARMO! Kliknite pre neobmedzený prístup!", 1),
    ("Nájdite si partnerku za 24 hodín! Overené zoznamovacie portály!", 1),

    # Technické podvody
    ("Váš počítač je infikovaný! Stiahnite antivírus ZADARMO ihneď!", 1),
    ("UPOZORNENIE: Váš softvér je zastaraný. Aktualizujte teraz zadarmo!", 1),
    ("Získajte Windows 11 Pro ZADARMO! Legálna licencia. Kliknite tu!", 1),
    ("Netflix Premium ZADARMO na 1 rok! Špeciálna akcia. Registrujte sa!", 1),
    ("Spotify Premium zdarma navždy! Tajný trik. Kliknite sem!", 1),
    ("Váš iPhone bol hacknutý! Stiahnite ochranu ihneď!", 1),
    ("Zadarmo VPN na neobmedzený čas! Skryte svoju aktivitu online!", 1),
    ("Hackujte WiFi susedov pomocou nášho nástroja. 100% funkčné!", 1),
    ("Zarábajte klikmi! 1 cent za klik. 500 EUR denne bez práce!", 1),
    ("Kliknite a získajte Amazon darčekovú kartu 500 EUR zadarmo!", 1),

    # Falošné správy a upozornenia
    ("DÔLEŽITÉ: Vaše predplatné vyprší o 24 hodín. Obnovte teraz!", 1),
    ("Posledné upozornenie: Váš účet bude deaktivovaný. Konajte hneď!", 1),
    ("Vaša zmluva s O2 bola automaticky predĺžená. Zrušte do 24 hodín!", 1),
    ("Orange: Vaše číslo bude prenesené. Zastavte prenos kliknutím tu!", 1),
    ("Telekom: Nezaplatený účet 89 EUR. Zaplaťte do zajtra alebo odpojenie!", 1),
    ("Sociálna poisťovňa: Máte nárok na vrátenie 450 EUR. Požiadajte tu!", 1),
    ("Ministerstvo financií: Daňový preplatok 320 EUR. Žiadajte vrátenie!", 1),
    ("Zdravotná poisťovňa: Nezaplatený príspevok. Uhraďte do 3 dní!", 1),
    ("RÝCHLE UPOZORNENIE: Vaša doména expiruje zajtra. Obnovte ihneď!", 1),
    ("Váš e-mail bude zmazaný pre nečinnosť. Prihláste sa a aktivujte ho!", 1),

    # Produkty a služby
    ("Ray-Ban okuliare 90% ZĽAVA! Len dnes. Objednajte za 9,99 EUR!", 1),
    ("Originálne hodinky Rolex za 99 EUR! Limitovaná ponuka. Kúpte teraz!", 1),
    ("Louis Vuitton kabelky za 49 EUR! Výpredaj skladu. Objednajte ihneď!", 1),
    ("Nike tenisky 80% ZĽAVA! Posledné kusy. Objednajte ešte dnes!", 1),
    ("iPhone 15 Pro za 299 EUR! Poškodený obal, plná funkčnosť. Kúpte!", 1),
    ("Samsung Galaxy S24 za 199 EUR! Výhodná kúpa. Obmedzené množstvo!", 1),
    ("Lacné letenky do Dubaja za 19 EUR! Len dnes. Rezervujte ihneď!", 1),
    ("Hotel 5* v Paríži za 29 EUR na noc! Špeciálna ponuka. Kliknite!", 1),
    ("Solárne panely ZADARMO! Štátna dotácia 100%. Požiadajte teraz!", 1),
    ("Tepelné čerpadlo za polovičnú cenu! Dotácia zahrnutá. Volajte!", 1),

    # Gamblovanie
    ("Kasíno bonus 1000 EUR zadarmo! Registrujte sa a hrajte bez rizika!", 1),
    ("Online poker: Získajte 500 EUR bonus pre nových hráčov!", 1),
    ("Stávkujte na futbal a zarobte! 100 EUR bonus pre nových hráčov!", 1),
    ("Ruleta online: Zdvojnásobte peniaze zaručene! Tajná stratégia!", 1),
    ("Hracie automaty online. 50 FREE SPINS zadarmo. Registrujte sa!", 1),

    # Vzdelávanie a diplomové podvody
    ("Získajte diplom VŠ za 3 mesiace! Uznávaný certifikát. Bez skúšok!", 1),
    ("Online kurz zarábania. Zarobte 10 000 EUR za mesiac. Záruka vrátenia!", 1),
    ("Certifikácia IT za víkend. Cisco, Microsoft diplom. Kliknite tu!", 1),
    ("Jazykový certifikát B2 bez skúšky! Legálny doklad. Objednajte!", 1),
    ("Vodičský preukaz bez autoškoly! Diskrétne a rýchlo. Informujte sa!", 1),

    # Rôzne spam kategórie
    ("Váš horoskop na tento mesiac odhaľuje šokujúce tajomstvo! Prečítajte!", 1),
    ("Jasnovidka Mária vidí vašu budúcnosť. Prvá konzultácia ZADARMO!", 1),
    ("Výherná kombinácia čísel pre loto tento týždeň! Kúpte tajomstvo!", 1),
    ("Zázračná voda lieči všetko! Vedci šokovaní. Objednajte 3+1 zadarmo!", 1),
    ("Pyramídová hra ZAKONNÁ v SR! Zarobte tisíce EUR za pár dní!", 1),
    ("Predajte nám vaše zlato za najlepšiu cenu! Hotovosť ihneď!", 1),
    ("Zbavte sa dlhov legálne! Osobný bankrot v 3 krokoch. Poradíme!", 1),
    ("Firemný register: Vaše údaje sú verejné! Skryte ich za 49 EUR!", 1),
    ("Ochrana osobných údajov GDPR. Zaplaťte 29 EUR alebo pokuta!", 1),
    ("Kliknite a sledujte živé zápasy ZADARMO! Bez registrácie!", 1),

    # Ďalší spam — miešané
    ("Predplatné zrušené. Vrátime vám 89 EUR. Zadajte číslo karty!", 1),
    ("Váš balík Amazon nie je možné doručiť. Aktualizujte adresu tu!", 1),
    ("Doručovateľ: Balík vrátený kvôli chýbajúcim colným poplatkom 6 EUR!", 1),
    ("Upozornenie FedEx: Zásilka pozastavená. Zaplaťte 3,49 EUR online!", 1),
    ("GLS: Váš balík čaká na vyzdvihnutie. Potvrďte doručovacie okno!", 1),
    ("FLASH SALE 95% ZĽAVA! Len nasledujúcich 10 minút. Kúpte teraz!", 1),
    ("Posledný kus! Objednajte ešte dnes za špeciálnu cenu 9,99 EUR!", 1),
    ("Špeciálna ponuka len pre vás! Exkluzívna zľava vyprší o polnoci!", 1),
    ("Reklamná výhra: Ste 1 000 000. zákazník! Cena čaká. Kliknite!", 1),
    ("Zaregistrujte sa a získajte ZADARMO darčekový kôš v hodnote 200 EUR!", 1),
    ("Ušetrite 500 EUR na poistení auta! Porovnajte ponuky zadarmo teraz!", 1),
    ("Refinancujte hypotéku a ušetrite 200 EUR mesačne! Volajte zadarmo!", 1),
    ("Energie lacnejšie o 40%! Premeňte si dodávateľa. Volajte ihneď!", 1),
    ("Solárna elektráreň na strechu ZADARMO! Štát platí všetko za vás!", 1),
    ("Teplovod SR: Odpojenie 15.3. Zaplaťte nedoplatok 234 EUR online!", 1),
    ("Lekárska štúdia hľadá dobrovoľníkov. Zárobok 500 EUR za víkend!", 1),
    ("Prenajmite vaše auto a zarobte 1000 EUR mesačne bez námahy!", 1),
    ("Predajte nám váš starý mobil! Platíme ihneď. Cena do 24 hodín!", 1),
    ("Záujem o prenájom bytu? Ponúkame 2-izbový byt za 200 EUR/mes!", 1),
    ("Záhradné práce: Pracovníci k dispozícii ihneď. Ceny od 5 EUR/hod!", 1),
    ("Upratovacia firma hľadá klientov. Prvé upratovanie ZADARMO!", 1),
    ("Maľovanie bytov lacno! Bez DPH. Volajte pre bezplatnú cenovú ponuku!", 1),
    ("Rekonštrukcia kúpeľne za polovičnú cenu! Akcia platí do konca mesiaca!", 1),
    ("Výmenné okná ZADARMO pri kúpe 3 kusov! Montáž v cene. Informujte sa!", 1),
    ("Klimatizácia za 499 EUR komplet s montážou! Obmedzená ponuka!", 1),
    ("Alarm pre dom za 1 EUR mesačne! Profesionálna ochrana. Kliknite!", 1),
    ("Zabezpečte rodinu! Životné poistenie od 5 EUR mesačne. Uzavrite online!", 1),
    ("Cestovné poistenie na rok za 19 EUR! Celá Európa. Objednajte teraz!", 1),
    ("Zarobte písaním článkov online! 50 EUR za článok. Bez skúseností!", 1),
    ("Prekladateľ hľadaný! Práca z domu 2000 EUR mesačne. Registrujte sa!", 1),

    # Anglické spam správy (model musí rozumieť aj im)
    ("CONGRATULATIONS! You have been selected for a cash prize of EU500,000!", 1),
    ("Make money fast! Work from home earn 5000 USD weekly guaranteed!", 1),
    ("Your account has been SUSPENDED. Verify immediately to restore access!", 1),
    ("FREE iPhone! You are our lucky visitor today. Click to claim now!", 1),
    ("Hot singles near you want to meet tonight! Free registration!", 1),
    ("Lose 20 pounds in 2 weeks! No diet no exercise. Miracle pill!", 1),
    ("Nigerian prince: I need your help transferring 4.5 million dollars!", 1),
    ("URGENT: Your PayPal is limited. Log in now to restore full access!", 1),
    ("Cheap meds online! Viagra Cialis no prescription needed. Order now!", 1),
    ("Double your Bitcoin in 24 hours! 100% guaranteed returns!", 1),

    # Spam v mix SK/EN
    ("UPOZORNENIE: Your account was accessed from unknown location! Verify now!", 1),
    ("Výhra! You won our weekly lottery prize of 10 000 EUR! Claim here!", 1),
    ("ZADARMO: Get your free iPhone 15 today! Len pre prvých 100 ľudí!", 1),
    ("Zarábajte online working from home! No experience needed. Start today!", 1),
    ("AKCIA: Buy 1 get 5 free! Len dnes. Limited stock. Order immediately!", 1),

    # Podvodné pracovné ponuky
    ("Práca v zahraničí: UK, Nemecko, Rakúsko. Plat 3000 EUR. Nástup ihneď!", 1),
    ("Hľadáme kuriérov na prepravu balíkov. Zárobky 200 EUR denne!", 1),
    ("Doma si vyrábajte výrobky a predávajte ich nám! Zárobky 1500 EUR!", 1),
    ("Modelka/model hľadaná. Platba 500 EUR za deň. Foto/video. Volajte!", 1),
    ("Asistent riaditeľa zahranič. firmy. 5000 EUR mes. Home office. Ihneď!", 1),
    ("Prepisovanie textov doma. 3 EUR za stranu. Neobmedzené množstvo!", 1),
    ("Testovanie produktov z domu. Produkty si necháte. + 200 EUR mesačne!", 1),
    ("Online recenzie a hodnotenia. 5 EUR za recenziu. Tisíce produktov!", 1),
    ("Klikajte na reklamy a zarábajte. 0,50 EUR za klik. Neobmedzene!", 1),
    ("Správa sociálnych médií z domu. 1500 EUR mesačne. Bez skúseností!", 1),

    # Podvody s nehnuteľnosťami
    ("Predám byt 3-izbový Bratislava 60 000 EUR! Naliehavý predaj. Volajte!", 1),
    ("Prenajmem chatu Tatry 50 EUR/noc! Rezervujte cez tento link!", 1),
    ("Investícia do nehnuteľností v Dubaji. Výnos 15% ročne. Informujte sa!", 1),
    ("Dom v Španielsku za 29 000 EUR! Priamy predaj od majiteľa. Kliknite!", 1),
    ("Záhradná chatka so pozemkom 5000 m2 za 15 000 EUR! Limitovaná ponuka!", 1),

    # Charita a podvody so zbierkami
    ("Pomôžte chorým deťom! Darujte 1 EUR a zachránite život!", 1),
    ("Zbierka pre vojnových utečencov. 100% ide priamo ľuďom v núdzi!", 1),
    ("Adoptujte zviera na diaľku za 2 EUR mesačne! Certifikát dostanete!", 1),
    ("Pomôžte nám postaviť nemocnicu v Afrike. Každé euro sa počíta!", 1),
    ("SOS! Rodina stratila všetko pri požiari. Prispejte cez tento účet!", 1),

    # ══════════════════════════════════════════════════════
    #  HAM — legitímne emaily (0) — 250 emailov
    # ══════════════════════════════════════════════════════

    # Pracovné emaily
    ("Ahoj, môžeme sa stretnúť zajtra o 10:00 na porade ohľadom projektu?", 0),
    ("V prílohe nájdete kvartálnu správu. Dajte vedieť ak máte otázky.", 0),
    ("Posielam zápisnicku z dnešného stretnutia. Prosím skontrolujte.", 0),
    ("Termín odovzdania projektu je presunutý na piatok 17:00.", 0),
    ("Potrebujem od vás podklady do stredy. Môžete mi ich poslať?", 0),
    ("Dobrý deň, potvrdzujem prijatie vašej objednávky č. 2024-1547.", 0),
    ("Prosím o schválenie faktúry č. 2024-089 do konca týždňa.", 0),
    ("Organizujem tímový obed v piatok. Môžete prísť o 12:00?", 0),
    ("Posielam aktualizovaný harmonogram projektu. Prosím skontrolujte.", 0),
    ("Máte čas na krátky hovor dnes popoludní ohľadom zmluvy?", 0),
    ("Pripomínam pracovnú poradu v utorok o 9:00 v zasadačke A.", 0),
    ("Váš návrh zmluvy bol prijatý. Podpísaná verzia v prílohe.", 0),
    ("Prosím o vypracovanie cenovej ponuky do piatku 12:00.", 0),
    ("Oznamujem, že od 1.4. budem na materskej dovolenke.", 0),
    ("Vyplňte prosím dochádzku za minulý mesiac do zajtra.", 0),
    ("Posiela sa nová verzia dokumentácie. Zmeny sú vyznačené červenou.", 0),
    ("Váš pracovný počítač je pripravený na prevzatie na IT oddelení.", 0),
    ("Stretnutie s klientom Novák sa presúva na štvrtok o 14:00.", 0),
    ("Prosím potvrďte prijatie tohto emailu. Dôležité podklady v prílohe.", 0),
    ("Náš tím dokončil analýzu. Výsledky prezentujeme v piatok o 10:00.", 0),

    # Osobné emaily
    ("Ahoj Miro, kedy si free na kávu? Rád by som sa stretol.", 0),
    ("Ďakujem za krásny darček k narodeninám! Veľmi ma potešil.", 0),
    ("Ako sa máš? Dlho sme sa nevideli. Daj vedieť ak budeš v meste.", 0),
    ("Môžeš mi požičať tú knihu o ktorej si rozprával? Zaujala ma.", 0),
    ("Pôjdeme cez víkend na výlet do Tatier? Počasie vyzerá skvelo!", 0),
    ("Posielam fotky z dovolenky. Bolo to nádherné! Určite odporúčam.", 0),
    ("Všetko najlepšie k narodeninám! Prajem ti veľa zdravia a šťastia.", 0),
    ("Plánujem oslavu 30-tín. Môžeš prísť v sobotu o 18:00?", 0),
    ("Nájdeš mi recept na tie skvele placky čo si robila minule?", 0),
    ("Rodičia prídu na návštevu budúci víkend. Môžeme sa stretnúť?", 0),

    # Školské a vzdelávacie emaily
    ("Vážený študent, skúškové obdobie začína 10. januára. Sledujte rozvrh.", 0),
    ("Prednáška z matematiky v stredu je zrušená. Náhradný termín oznámime.", 0),
    ("Vaša záverečná práca bola prijatá na hodnotenie. Obhajoba 15.6.", 0),
    ("Stipendijná komisia rozhodla o pridelení štipendia vo výške 200 EUR.", 0),
    ("Prihlasovanie na výberové predmety prebieha do 28. februára.", 0),
    ("Výsledky prijímacích skúšok budú zverejnené 30. júna na webe školy.", 0),
    ("Školský výlet do Viedne je plánovaný na 15. marca. Poplatok 45 EUR.", 0),
    ("Rodičovské združenie sa koná v pondelok o 17:00 v triede 5.B.", 0),
    ("Vaše učebnice sú pripravené na prevzatie v školskej knižnici.", 0),
    ("Súťaž v matematike prebieha 5. novembra. Prihlasujte sa do 1.11.", 0),

    # E-commerce a objednávky
    ("Vaša objednávka č. SK-2024-8847 bola úspešne prijatá.", 0),
    ("Balík bol odoslaný. Sledovacie číslo: SK123456789. Doručenie zajtra.", 0),
    ("Váš tovar bol doručený do výdajného miesta Packeta v Košiciach.", 0),
    ("Reklamácia č. 2024-123 bola prijatá. Vybavenie do 30 dní.", 0),
    ("Potvrdzujeme vrátenie platby 89 EUR na vašu kartu do 5 dní.", 0),
    ("Produkt ktorý ste sledovali je opäť dostupný na sklade.", 0),
    ("Vaša rezervácia v reštaurácii Koliba na sobotu o 19:00 je potvrdená.", 0),
    ("Lístky na koncert Užovka 15.5. boli zaslané na váš email.", 0),
    ("Vaša predplatná kartička Tesco Clubcard bola obnovená.", 0),
    ("Nákup v IKEA: Montáž nábytku je naplánovaná na sobotu 9:00-12:00.", 0),

    # Bankovníctvo a financie (legitímne)
    ("Výpis z účtu za mesiac február bol vygenerovaný. Dostupný v appke.", 0),
    ("Trvalý príkaz na nájomné 450 EUR bol úspešne vykonaný.", 0),
    ("Vaša žiadosť o hypotéku bola postúpená na schválenie. Čakajte 5 dní.", 0),
    ("Kreditná karta končí platnosť 12/2024. Nová bude zaslaná poštou.", 0),
    ("SEPA prevod 1200 EUR na účet bol úspešne odoslaný.", 0),
    ("Mesačný výpis z kreditnej karty: Obrat 342,50 EUR. Splatnosť 15.3.", 0),
    ("Vaše sporenie Zlatý fond: Aktuálny zostatok 8 450 EUR k 1.3.2024.", 0),
    ("Potvrdenie: Hotovostný vklad 500 EUR na pobočke bol zaznamenaný.", 0),
    ("Vaša PIN zmena bola úspešne dokončená. Nový PIN aktivovaný.", 0),
    ("Upozornenie: Zostatok na účte klesol pod 50 EUR. Aktuálny: 38,20 EUR.", 0),

    # Zdravotníctvo (legitímne)
    ("Termín k lekárovi MUDr. Kováč je potvrdený na stredu 14:00.", 0),
    ("Výsledky krvných testov sú dostupné v systéme eZdravie.", 0),
    ("Pripomíname preventívnu prehliadku. Objednajte sa na tel. 02/1234567.", 0),
    ("Váš recept bol predĺžený. Môžete si ho vyzdvihnúť v lekárni.", 0),
    ("Ambulancia bude zatvorená 24-25. decembra. Pohotovosť: 02/9876543.", 0),
    ("Výsledky mamografického vyšetrenia: Nález je v poriadku. Kontrola o rok.", 0),
    ("Zubná ambulancia: Vaše zuby budú ošetrené v piatok o 10:30.", 0),
    ("Rehabilitácia: 10 procedúr schválených poisťovňou. Začiatok pondelok.", 0),
    ("Psychiatrická ambulancia: Nasledujúce stretnutie 20.3. o 11:00.", 0),
    ("Zdravotná poisťovňa: Ročné zúčtovanie zdravotného poistenia v prílohe.", 0),

    # Štátna správa a úrady
    ("Žiadosť o rodný list bola vybavená. Dokument si vyzdvihnite na matrike.", 0),
    ("Váš pas bol vyhotovený. Prevzatie na oddelení dokladov od 5.4.", 0),
    ("Daňové priznanie za rok 2023 bolo prijaté. Preplatok: 180 EUR.", 0),
    ("Výzva na zaplatenie miestneho poplatku za komunálny odpad: 35 EUR.", 0),
    ("Stavebné povolenie č. 2024-SP-1547 bolo vydané. Platnosť 2 roky.", 0),
    ("Sociálna poisťovňa: Výška dôchodku od 1.1.2024 je 580 EUR mesačne.", 0),
    ("Úrad práce: Vaša žiadosť o dávku v nezamestnanosti bola schválená.", 0),
    ("Kataster nehnuteľností: Zmena vlastníka bytu bola zapísaná do katastra.", 0),
    ("Volebné oznámenie: Voľby do Národnej rady sa konajú 30. septembra.", 0),
    ("Magistrát: Vaša sťažnosť č. 2024-847 bola postúpená na vybavenie.", 0),

    # Cestovanie a voľný čas
    ("Rezervácia letu OK-1234 Bratislava-Londýn 15.6. je potvrdená.", 0),
    ("Hotel Panorama Vysoké Tatry: Check-in 22.7. o 15:00. Tešíme sa!", 0),
    ("Požičovňa auta: Vozidlo Škoda Octavia pripravené na prevzatie v piatok.", 0),
    ("Turistická trasa Rysy je otvorená od 1. júna. Podmienky na webe.", 0),
    ("Filmové lístky na Barbie v sobotu o 20:15 v kine Lumière potvrdené.", 0),
    ("Knižnica: Rezervovaná kniha Sapiens je pripravená na vyzdvihnutie.", 0),
    ("Fitnescentrum: Vaše predplatné bolo obnovené na ďalší mesiac.", 0),
    ("Plavecký bazén: Prenájom dráhy v sobotu o 8:00 je potvrdený.", 0),
    ("Hudobná škola: Hodina klavíra v utorok o 16:00 prebehne online.", 0),
    ("Záhradné centrum: Vaša objednávka stromčekov je pripravená na vyzdvihnutie.", 0),

    # IT a technológie (legitímne)
    ("Aktualizácia systému prebehne v noci z piatku na sobotu 2:00-4:00.", 0),
    ("Váš GitHub Pull Request bol schválený a zlúčený do main vetvy.", 0),
    ("Serverová záloha bola úspešne dokončená. Veľkosť: 45 GB.", 0),
    ("SSL certifikát domény vyprší za 30 dní. Prosím obnovte ho.", 0),
    ("Nová verzia aplikácie 2.4.1 je dostupná v App Store.", 0),
    ("Bezpečnostná aktualizácia systému Windows je pripravená na inštaláciu.", 0),
    ("Váš Jira ticket #2847 bol uzavretý. Riešenie v komentároch.", 0),
    ("Daily standup je presunutý na 9:30. Google Meet link ostáva rovnaký.", 0),
    ("Testovanie nových funkcií prebieha na staging prostredí od dnes.", 0),
    ("Code review k vašemu PR bol dokončený. 3 komentáre na opravu.", 0),

    # Komunita a susedia
    ("Správa bytového domu: Výmena výťahu prebehne 15.-17. marca.", 0),
    ("Schôdza vlastníkov bytov sa koná v stredu o 18:00 vo vchode č. 3.", 0),
    ("Upozornenie: Prerušenie dodávky teplej vody 20.3. od 8:00 do 16:00.", 0),
    ("Bytové družstvo: Predpis záloh na rok 2024 v prílohe.", 0),
    ("Susedia, v sobotu robíme brigádu v záhrade. Prosím príďte pomôcť!", 0),
    ("Obec Vrbové: Separovaný zber plastov prebehne 12. apríla.", 0),
    ("Miestny futbalový klub hľadá dobrovoľníkov na organizáciu zápasov.", 0),
    ("Kultúrny dom: Divadelné predstavenie Cyrano o 19:00 v piatok.", 0),
    ("Hasiči Trenčín: Ďakujeme za príspevok na nové vybavenie.", 0),
    ("Farský úrad: Omša za zosnulých sa koná v pondelok o 18:00.", 0),

    # Rodina a domácnosť
    ("Mamina, nezabudni zajtra zobrať Petra z tréningu o 17:30.", 0),
    ("Objednala som servis auta na piatok o 9:00 do Aurela. Môžeš ísť?", 0),
    ("Poistenie domu vyprší 31.3. Stačí podpísať predĺženie a poslať späť.", 0),
    ("Elektrikár príde v stredu medzi 10:00-12:00. Prosím buď doma.", 0),
    ("Kúpila som lístky na rodinný výlet do ZOO na sobotu pre 4 osoby.", 0),
    ("Plánujeme Vianoce u babičky. Môžete prísť 24.12. na obed o 12:00?", 0),
    ("Detský lekár: Petko má kontrolu v piatok o 8:30. Nezabudnite očkovací.", 0),
    ("Základná škola: Triedna schôdza sa koná 15.10. o 17:00 v triede.", 0),
    ("Školská jedáleň: Strava bude od septembra stáť 1,65 EUR na deň.", 0),
    ("Táborový vedúci: Registrácia na letný tábor otvárá 1. marca o 8:00.", 0),

    # Zamestnávanie (legitímne ponuky)
    ("Vaša žiadosť o prácu na pozíciu Softvérový inžinier bola prijatá.", 0),
    ("Pozývame vás na pracovný pohovor v stredu o 10:00 na naše sídlo.", 0),
    ("Vaše CV bolo zaradené do databázy vhodných kandidátov. Ďakujeme.", 0),
    ("Pracovná ponuka: Účtovník, plat 1800 EUR, Bratislava, nástup dohodou.", 0),
    ("Podpis pracovnej zmluvy je naplánovaný na pondelok o 9:00 v HR.", 0),
    ("Nástupné školenie prebehne prvý týždeň marca. Program v prílohe.", 0),
    ("Benefity pre nových zamestnancov: Stravné lístky, home office, auto.", 0),
    ("Hodnotenie zamestnanca na rok 2023: Výborné. Odmena 500 EUR.", 0),
    ("Zmena pracovného času od 1.4.: Začiatok o 8:00 namiesto 9:00.", 0),
    ("HR oddelenie: Prosím vyplňte formulár na objednanie straveniek do piatku.", 0),

    # Rôzne legitímne správy
    ("Newsletter: Nové pravidlá ochrany osobných údajov platné od 1.5.2024.", 0),
    ("Váš komentár na produkt bol schválený a zverejnený. Ďakujeme!", 0),
    ("Potvrdzujeme zmenu hesla k vášmu účtu. Ak ste to neboli vy, kontaktujte nás.", 0),
    ("Dvojfaktorové overenie bolo úspešne aktivované na vašom účte.", 0),
    ("Vaše predplatné Netflix sa obnoví 15. marca. Suma: 15,99 EUR.", 0),
    ("Spotify: Vaša playlist Obľúbené bola zdieľaná so 3 priateľmi.", 0),
    ("LinkedIn: Máte 5 nových spojení čakajúcich na potvrdenie.", 0),
    ("Nová správa od Petra Nováka na platforme Slack.", 0),
    ("Zoom stretnutie: Odkaz na dnešný webinár o kybernetickej bezpečnosti.", 0),
    ("Microsoft Teams: Váš tím vás pozýva na virtuálny tímový building.", 0),
    ("Vaša recenzia knihy bola oceňená 47 ľuďmi ako užitočná.", 0),
    ("Podcast Slovensko v súvislostiach: Nová epizóda je dostupná.", 0),
    ("Vaša donácia 10 EUR pre Červený kríž bola spracovaná. Ďakujeme!", 0),
    ("Crowdfunding: Projekt Slovenský film dosiahol 80% cieľovej sumy!", 0),
    ("Autopredajňa: Technická kontrola vášho vozidla vyprší 30.6.2024.", 0),
    ("Poistenie vozidla: Poistné na rok 2024 je 389 EUR. Výzva v prílohe.", 0),
    ("STK stanica: Termín technickej kontroly je potvrdený na 18.4. o 14:00.", 0),
    ("Čerpacia stanica Shell: Body za tankovanie - aktuálny stav: 1250 bodov.", 0),
    ("Veterinárna klinika: Očkovanie Rexka je naplánované na 5. mája o 10:00.", 0),
    ("Záchranná stanica: Mačička čo ste našli sa úspešne zotavila. Ďakujeme!", 0),
]

def add_to_db():
    if not os.path.exists(DB_PATH):
        print(f"CHYBA: Databáza nenájdená na ceste: {DB_PATH}")
        print("Uistite sa, že app.py bežal aspoň raz a databáza bola vytvorená.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    pridane = 0
    for text, label in SLOVAK_EMAILS:
        c.execute("INSERT INTO emails (text, label, source) VALUES (?, ?, ?)",
                  (text, label, "slovak_dataset"))
        pridane += 1

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    spam  = conn.execute("SELECT COUNT(*) FROM emails WHERE label=1").fetchone()[0]
    ham   = conn.execute("SELECT COUNT(*) FROM emails WHERE label=0").fetchone()[0]
    conn.close()

    print(f"✅ Pridaných {pridane} slovenských emailov do databázy.")
    print(f"📊 Celkový stav: {total} emailov ({spam} spam, {ham} ham)")
    print(f"\n⚙️  Teraz reštartujte server (Ctrl+C a znova python app.py)")
    print(f"   alebo kliknite 'Znovu natrénovať' v aplikácii.")

if __name__ == "__main__":
    add_to_db()
