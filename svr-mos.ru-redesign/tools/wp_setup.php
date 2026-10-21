<?php
// Локальный стенд WordPress 7.1.3 + SQLite для превью дизайн-системы. Запуск: php tools/wp_setup.php
$R = dirname( __DIR__ );
require $R . '/tmp/wp/core/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
require_once ABSPATH . 'wp-admin/includes/post.php';
wp_set_current_user( 1 );
switch_theme( 'twentytwentyfive' );
update_option( 'permalink_structure', '/%postname%/' );
update_option( 'WPLANG', 'ru_RU' );
update_option( 'blogname', 'СВР' );
update_option( 'blogdescription', 'Сервис водных ресурсов' );
// удалить демо-записи
foreach ( array( 1, 2, 3 ) as $pid ) { if ( get_post( $pid ) ) wp_delete_post( $pid, true ); }
$media = json_decode( file_get_contents( dirname( $R ) . '/media.json' ), true );
$up = wp_upload_dir( '2026/10' );
foreach ( $media as $m ) {
  if ( get_post( $m['id'] ) ) continue;
  $name = basename( $m['url'] );
  $dest = $up['path'] . '/' . $name;
  copy( $m['local'], $dest );
  $ft = wp_check_filetype( $name );
  $aid = wp_insert_attachment( array(
    'import_id' => $m['id'], 'post_title' => pathinfo( $name, PATHINFO_FILENAME ), 'post_mime_type' => $ft['type'],
    'post_status' => 'inherit', 'guid' => $m['url'],
  ), $dest );
  if ( $aid !== $m['id'] ) echo "WARN id {$m['id']} -> $aid\n";
  if ( str_starts_with( $ft['type'], 'image/' ) ) {
    wp_update_attachment_metadata( $aid, wp_generate_attachment_metadata( $aid, $dest ) );
  }
}
$pages = array( 49 => array( 'home', 'Главная' ), 50 => array( 'obj', 'Наши объекты' ), 51 => array( 'elteza', 'ОАО «Элтеза»' ),
  52 => array( 'russkii', 'ОАО «Мясокомбинат «Рузский»' ), 53 => array( 'os3-marino', 'ОС3 Марьино-Саларьево (II этап)' ),
  54 => array( 'os2-marino', 'ОС2 Марьино-Саларьево (II этап)' ), 55 => array( 'prod', 'Наша продукция' ), 56 => array( 'docs', 'Документы' ),
  57 => array( 'rekvizit', 'Реквизиты компании' ), 58 => array( 'contact', 'Контакты' ) );
foreach ( $pages as $id => $p ) {
  if ( get_post( $id ) ) continue;
  $r = wp_insert_post( array( 'import_id' => $id, 'post_type' => 'page', 'post_status' => 'publish', 'post_name' => $p[0], 'post_title' => $p[1],
    'post_content' => '<!-- wp:paragraph --><p>Черновик.</p><!-- /wp:paragraph -->' ) );
  if ( $r !== $id ) echo "WARN page $id -> $r\n";
}
update_option( 'site_logo', 7 );
update_option( 'show_on_front', 'page' );
update_option( 'page_on_front', 49 );
flush_rewrite_rules();
echo "ok\n";
