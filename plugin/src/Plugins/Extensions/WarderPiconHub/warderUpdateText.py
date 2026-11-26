"""Shared Warder updater wording. Keep this file identical in both projects."""
TEXT = {'sk': {'offer': 'Dostupná je nová verzia %s.\n\nNainštalovaná: %s\nNová verzia: %s\n\n%s\n\nNainštalovať aktualizáciu?', 'progress': 'Sťahujem a overujem aktualizáciu pluginu.\nPočas inštalácie nevypínajte prijímač.', 'success': 'Plugin bol aktualizovaný na verziu %s.\nO 3 sekundy sa reštartuje GUI.', 'current': 'Máš aktuálnu verziu, nie je potrebná aktualizácia.', 'error': 'Aktualizácia pluginu zlyhala.\n\n', 'confirm': 'Potvrdiť'}, 'en': {'offer': 'A new %s version is available.\n\nInstalled: %s\nNew version: %s\n\n%s\n\nInstall the update?', 'progress': 'Downloading and verifying the plugin update.\nDo not turn off the receiver during installation.', 'success': 'Plugin updated to version %s.\nThe GUI will restart in 3 seconds.', 'current': 'You have the current version; no update is needed.', 'error': 'Plugin update failed.\n\n', 'confirm': 'Confirm'}, 'cs': {'offer': 'Je dostupná nová verze %s.\n\nNainstalováno: %s\nNová verze: %s\n\n%s\n\nNainstalovat aktualizaci?', 'progress': 'Stahuji a ověřuji aktualizaci pluginu.\nBěhem instalace nevypínejte přijímač.', 'success': 'Plugin byl aktualizován na verzi %s.\nZa 3 sekundy se restartuje GUI.', 'current': 'Máš aktuální verzi, aktualizace není potřebná.', 'error': 'Aktualizace pluginu selhala.\n\n', 'confirm': 'Potvrdit'}, 'de': {'offer': 'Eine neue Version von %s ist verfügbar.\n\nInstalliert: %s\nNeue Version: %s\n\n%s\n\nUpdate installieren?', 'progress': 'Plugin-Update wird geladen und geprüft.\nReceiver während der Installation nicht ausschalten.', 'success': 'Plugin auf Version %s aktualisiert.\nDie GUI startet in 3 Sekunden neu.', 'current': 'Die aktuelle Version ist installiert. Kein Update erforderlich.', 'error': 'Plugin-Update fehlgeschlagen.\n\n', 'confirm': 'Bestätigen'}, 'pl': {'offer': 'Dostępna jest nowa wersja %s.\n\nZainstalowano: %s\nNowa wersja: %s\n\n%s\n\nZainstalować aktualizację?', 'progress': 'Pobieranie i weryfikowanie aktualizacji wtyczki.\nNie wyłączaj odbiornika podczas instalacji.', 'success': 'Wtyczka zaktualizowana do wersji %s.\nGUI uruchomi się ponownie za 3 sekundy.', 'current': 'Masz aktualną wersję, aktualizacja nie jest potrzebna.', 'error': 'Aktualizacja wtyczki nie powiodła się.\n\n', 'confirm': 'Potwierdź'}, 'hu': {'offer': 'Elérhető a %s új verziója.\n\nTelepítve: %s\nÚj verzió: %s\n\n%s\n\nTelepíted a frissítést?', 'progress': 'A bővítményfrissítés letöltése és ellenőrzése.\nTelepítés közben ne kapcsold ki a vevőt.', 'success': 'A bővítmény frissült erre a verzióra: %s.\nA GUI 3 másodperc múlva újraindul.', 'current': 'A jelenlegi verzió van telepítve, nincs szükség frissítésre.', 'error': 'A bővítményfrissítés sikertelen.\n\n', 'confirm': 'Megerősítés'}, 'ru': {'offer': 'Доступна новая версия %s.\n\nУстановлена: %s\nНовая версия: %s\n\n%s\n\nУстановить обновление?', 'progress': 'Загрузка и проверка обновления плагина.\nНе выключайте ресивер во время установки.', 'success': 'Плагин обновлён до версии %s.\nGUI перезапустится через 3 секунды.', 'current': 'Установлена актуальная версия, обновление не требуется.', 'error': 'Не удалось обновить плагин.\n\n', 'confirm': 'Подтвердить'}, 'fr': {'offer': 'Une nouvelle version de %s est disponible.\n\nInstallée : %s\nNouvelle version : %s\n\n%s\n\nInstaller la mise à jour ?', 'progress': "Téléchargement et vérification de la mise à jour.\nN'éteignez pas le récepteur pendant l'installation.", 'success': "Plugin mis à jour vers la version %s.\nL'interface redémarrera dans 3 secondes.", 'current': 'La version actuelle est installée, aucune mise à jour n’est nécessaire.', 'error': 'Échec de la mise à jour du plugin.\n\n', 'confirm': 'Confirmer'}, 'it': {'offer': "È disponibile una nuova versione di %s.\n\nInstallata: %s\nNuova versione: %s\n\n%s\n\nInstallare l'aggiornamento?", 'progress': "Download e verifica dell'aggiornamento del plugin.\nNon spegnere il ricevitore durante l'installazione.", 'success': 'Plugin aggiornato alla versione %s.\nLa GUI si riavvierà tra 3 secondi.', 'current': 'È installata la versione attuale, non è necessario aggiornare.', 'error': 'Aggiornamento del plugin non riuscito.\n\n', 'confirm': 'Conferma'}, 'es': {'offer': 'Hay una nueva versión de %s.\n\nInstalada: %s\nNueva versión: %s\n\n%s\n\n¿Instalar la actualización?', 'progress': 'Descargando y verificando la actualización del plugin.\nNo apagues el receptor durante la instalación.', 'success': 'Plugin actualizado a la versión %s.\nLa interfaz se reiniciará en 3 segundos.', 'current': 'Tienes la versión actual, no es necesario actualizar.', 'error': 'Error al actualizar el plugin.\n\n', 'confirm': 'Confirmar'}}

# Additional Warder languages use the same wording as the shared catalog.
TEXT.update({
    "al": {
        "offer": "Një version i ri i %s është i disponueshëm.\n\nInstaluar: %s\nVersioni i ri: %s\n\n%s\n\nTë instalohet përditësimi?",
        "progress": "Po shkarkohet dhe verifikohet përditësimi i shtojcës.\nMos e fik marrësin gjatë instalimit.",
        "success": "Shtojca u përditësua në versionin %s.\nNdërfaqja do të riniset pas 3 sekondash.",
        "current": "Ke versionin aktual; nuk nevojitet përditësim.",
        "error": "Përditësimi i shtojcës dështoi.\n\n",
        "confirm": "Konfirmo"
    },
    "el": {
        "offer": "Διατίθεται νέα έκδοση του %s.\n\nΕγκατεστημένη: %s\nΝέα έκδοση: %s\n\n%s\n\nΕγκατάσταση ενημέρωσης;",
        "progress": "Λήψη και επαλήθευση ενημέρωσης πρόσθετου.\nΜην απενεργοποιήσετε τον δέκτη κατά την εγκατάσταση.",
        "success": "Το πρόσθετο ενημερώθηκε στην έκδοση %s.\nΤο γραφικό περιβάλλον θα επανεκκινηθεί σε 3 δευτερόλεπτα.",
        "current": "Έχετε την τρέχουσα έκδοση· δεν απαιτείται ενημέρωση.",
        "error": "Η ενημέρωση του πρόσθετου απέτυχε.\n\n",
        "confirm": "Επιβεβαίωση"
    },
    "et": {
        "offer": "Saadaval on %si uus versioon.\n\nPaigaldatud: %s\nUus versioon: %s\n\n%s\n\nPaigaldada uuendus?",
        "progress": "Plugina uuenduse allalaadimine ja kontrollimine.\nÄra lülita vastuvõtjat paigaldamise ajal välja.",
        "success": "Plugin uuendati versioonile %s.\nKasutajaliides taaskäivitub 3 sekundi pärast.",
        "current": "Sul on praegune versioon; uuendust pole vaja.",
        "error": "Plugina uuendamine ebaõnnestus.\n\n",
        "confirm": "Kinnita"
    },
    "fa": {
        "offer": "نسخه جدید %s در دسترس است.\n\nنسخه نصب‌شده: %s\nنسخه جدید: %s\n\n%s\n\nبه‌روزرسانی نصب شود؟",
        "progress": "در حال دانلود و بررسی به‌روزرسانی افزونه.\nهنگام نصب گیرنده را خاموش نکنید.",
        "success": "افزونه به نسخه %s به‌روز شد.\nرابط کاربری پس از ۳ ثانیه راه‌اندازی مجدد می‌شود.",
        "current": "نسخه فعلی را دارید؛ نیازی به به‌روزرسانی نیست.",
        "error": "به‌روزرسانی افزونه ناموفق بود.\n\n",
        "confirm": "تأیید"
    },
    "lt": {
        "offer": "Yra nauja %s versija.\n\nĮdiegta: %s\nNauja versija: %s\n\n%s\n\nĮdiegti naujinimą?",
        "progress": "Atsisiunčiamas ir tikrinamas papildinio naujinimas.\nNeišjunkite imtuvo diegimo metu.",
        "success": "Papildinys atnaujintas į versiją %s.\nSąsaja bus paleista iš naujo po 3 sekundžių.",
        "current": "Turite dabartinę versiją; naujinti nereikia.",
        "error": "Papildinio naujinimas nepavyko.\n\n",
        "confirm": "Patvirtinti"
    },
    "nl": {
        "offer": "Er is een nieuwe versie van %s beschikbaar.\n\nGeïnstalleerd: %s\nNieuwe versie: %s\n\n%s\n\nUpdate installeren?",
        "progress": "Plugin-update downloaden en controleren.\nSchakel de ontvanger tijdens de installatie niet uit.",
        "success": "Plugin bijgewerkt naar versie %s.\nDe GUI start over 3 seconden opnieuw.",
        "current": "Je hebt de huidige versie; er is geen update nodig.",
        "error": "Plugin-update mislukt.\n\n",
        "confirm": "Bevestigen"
    },
    "pt": {
        "offer": "Está disponível uma nova versão do %s.\n\nInstalada: %s\nNova versão: %s\n\n%s\n\nInstalar a atualização?",
        "progress": "A transferir e verificar a atualização do plugin.\nNão desligue o recetor durante a instalação.",
        "success": "Plugin atualizado para a versão %s.\nA interface reiniciará em 3 segundos.",
        "current": "Tem a versão atual; não é necessário atualizar.",
        "error": "Falha na atualização do plugin.\n\n",
        "confirm": "Confirmar"
    },
    "ro": {
        "offer": "Este disponibilă o versiune nouă a %s.\n\nInstalată: %s\nVersiune nouă: %s\n\n%s\n\nInstalezi actualizarea?",
        "progress": "Se descarcă și se verifică actualizarea pluginului.\nNu opri receptorul în timpul instalării.",
        "success": "Plugin actualizat la versiunea %s.\nInterfața va reporni în 3 secunde.",
        "current": "Ai versiunea actuală; nu este necesară actualizarea.",
        "error": "Actualizarea pluginului a eșuat.\n\n",
        "confirm": "Confirmă"
    },
    "tr": {
        "offer": "%s için yeni bir sürüm mevcut.\n\nYüklü: %s\nYeni sürüm: %s\n\n%s\n\nGüncelleme yüklensin mi?",
        "progress": "Eklenti güncellemesi indiriliyor ve doğrulanıyor.\nKurulum sırasında alıcıyı kapatmayın.",
        "success": "Eklenti %s sürümüne güncellendi.\nArayüz 3 saniye içinde yeniden başlayacak.",
        "current": "Güncel sürüm yüklü; güncelleme gerekmiyor.",
        "error": "Eklenti güncellemesi başarısız oldu.\n\n",
        "confirm": "Onayla"
    },
    "uk": {
        "offer": "Доступна нова версія %s.\n\nВстановлено: %s\nНова версія: %s\n\n%s\n\nВстановити оновлення?",
        "progress": "Завантаження та перевірка оновлення плагіна.\nНе вимикайте ресивер під час встановлення.",
        "success": "Плагін оновлено до версії %s.\nІнтерфейс перезапуститься через 3 секунди.",
        "current": "У вас актуальна версія, оновлення не потрібне.",
        "error": "Не вдалося оновити плагін.\n\n",
        "confirm": "Підтвердити"
    },
    "zh": {
        "offer": "%s 有新版本可用。\n\n已安装：%s\n新版本：%s\n\n%s\n\n安装更新？",
        "progress": "正在下载并验证插件更新。\n安装期间请勿关闭接收机。",
        "success": "插件已更新至 %s 版本。\n界面将在 3 秒后重启。",
        "current": "您已安装最新版本，无需更新。",
        "error": "插件更新失败。\n\n",
        "confirm": "确认"
    }
})

ALIASES = {"sq": "al", "gr": "el", "cz": "cs", "ua": "uk", "cn": "zh"}


def language_code(language):
    code = str(language or "en").split(".")[0].replace("-", "_").split("_")[0].lower()
    return ALIASES.get(code, code)


def update_text(kind, product, current="", new="", notes="", error="", language="en"):
    lang = language_code(language)
    text = TEXT.get(lang, TEXT["en"])[kind]
    if kind == "confirm":
        return text
    if kind == "offer":
        return text % (product, current, new, notes)
    if kind == "success":
        return product + "\n\n" + text % new
    if kind == "current":
        return product + "\n\n" + text + "\n\n" + current
    if kind == "error":
        return product + "\n\n" + text + error
    return product + "\n\n" + text
