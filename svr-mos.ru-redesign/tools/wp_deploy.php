<?php
// Устарело: раньше деплоило tmp/canon/<id>.html (перегенерируемые черновики — затирали правки ревью).
// Теперь деплой на ЛОКАЛЬНЫЙ стенд — только пакетом deploy/ по manifest.json: php tools/apply_manifest.php
require __DIR__ . '/apply_manifest.php';
