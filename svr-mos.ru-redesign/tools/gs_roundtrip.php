<?php
// Проверка на ЛОКАЛЬНОМ стенде (redesign/tmp/wp): POST global-styles.json → GET context=edit → что WP отбросил/изменил.
// Сайт не трогается. Запуск: php tools/gs_roundtrip.php [путь к global-styles.json]
$R = dirname( __DIR__ );
require $R . '/tmp/wp/core/wp-load.php';
wp_set_current_user( 1 );
$file = $argv[1] ?? "$R/system/global-styles.json";
$sent = json_decode( file_get_contents( $file ), true );
$id = WP_Theme_JSON_Resolver::get_user_global_styles_post_id();
$req = new WP_REST_Request( 'POST', "/wp/v2/global-styles/$id" );
$req->set_header( 'Content-Type', 'application/json' );
$req->set_body( wp_json_encode( $sent ) );
$res = rest_do_request( $req );
echo 'POST status: ' . $res->get_status() . "\n";
if ( $res->get_status() >= 300 ) { echo wp_json_encode( $res->get_data() ) . "\n"; exit( 1 ); }
$get = new WP_REST_Request( 'GET', "/wp/v2/global-styles/$id" );
$get->set_param( 'context', 'edit' );
$got = rest_do_request( $get )->get_data();
$back = array( 'settings' => $got['settings'], 'styles' => $got['styles'] );
function flat( $a, $p = '' ) { $o = array(); foreach ( (array) $a as $k => $v ) { $kp = $p . '/' . $k; if ( is_array( $v ) && $v && array_keys( $v ) !== range( 0, count( $v ) - 1 ) ) { $o += flat( $v, $kp ); } else { $o[ $kp ] = $v; } } return $o; }
$fs = flat( $sent ); $fb = flat( $back );
$dropped = array_diff_key( $fs, $fb ); $added = array_diff_key( $fb, $fs ); $changed = array();
foreach ( array_intersect_key( $fs, $fb ) as $k => $v ) { if ( $v !== $fb[ $k ] ) $changed[ $k ] = array( $v, $fb[ $k ] ); }
echo 'dropped by WP: ' . count( $dropped ) . "\n"; foreach ( $dropped as $k => $v ) echo "  - $k\n";
echo 'added by WP: ' . count( $added ) . "\n"; foreach ( $added as $k => $v ) echo "  + $k = " . substr( wp_json_encode( $v ), 0, 120 ) . "\n";
echo 'changed: ' . count( $changed ) . "\n"; foreach ( $changed as $k => $v ) echo "  ~ $k: " . substr( wp_json_encode( $v[0] ), 0, 80 ) . ' -> ' . substr( wp_json_encode( $v[1] ), 0, 80 ) . "\n";
// Сгенерированный CSS фронтенда: есть ли в нём наш styles.css и стили вариации outline
$css = wp_get_global_stylesheet();
echo 'global stylesheet bytes: ' . strlen( $css ) . "\n";
echo 'custom css (wp_get_global_styles_custom_css) bytes: ' . strlen( wp_get_global_styles_custom_css() ) . "\n";
