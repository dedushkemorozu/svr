<?php
/**
 * Одноразовый сборщик эталонных данных WordPress для preview.py.
 *
 * Запуск (против ЛОКАЛЬНОЙ копии WP 7.1.3 + TT5, не против сайта):
 *   php tools/wp_dump_data.php <путь-к-wp-core> <папка-вывода>
 *
 * Пишет:
 *   theme-base.json   — объединённые данные theme.json: default + blocks + theme (без пользовательских global styles)
 *   blocks.json       — метаданные всех зарегистрированных блоков: селекторы для global styles,
 *                       supports, атрибуты по умолчанию, динамический ли блок
 *   wp-version.txt    — версия WP и темы
 */

if ( $argc < 3 ) {
	fwrite( STDERR, "usage: php wp_dump_data.php <wp-core-dir> <out-dir>\n" );
	exit( 1 );
}
$core = rtrim( $argv[1], '/' );
$out  = rtrim( $argv[2], '/' );

define( 'WP_USE_THEMES', false );
$_SERVER['REQUEST_URI'] = '/';
require $core . '/wp-load.php';

function svr_json( $data ) {
	return wp_json_encode( $data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
}

// 1. theme.json: default + blocks + theme.
$base = WP_Theme_JSON_Resolver::get_merged_data( 'theme' );
file_put_contents( "$out/theme-base.json", svr_json( $base->get_raw_data() ) );

// 2. Метаданные блоков.
$ref = new ReflectionMethod( 'WP_Theme_JSON', 'get_blocks_metadata' );
$ref->setAccessible( true );
$meta = $ref->invoke( null );

$registry = WP_Block_Type_Registry::get_instance();
$blocks   = array();
foreach ( $registry->get_all_registered() as $name => $bt ) {
	$defaults = array();
	foreach ( (array) $bt->attributes as $attr => $schema ) {
		if ( is_array( $schema ) && array_key_exists( 'default', $schema ) ) {
			$defaults[ $attr ] = $schema['default'];
		}
	}
	$blocks[ $name ] = array(
		'selector'        => $meta[ $name ]['selector'] ?? null,
		'selectors'       => $meta[ $name ]['selectors'] ?? array(),
		'elements'        => $meta[ $name ]['elements'] ?? array(),
		'duotone'         => $meta[ $name ]['duotone'] ?? null,
		'styleVariations' => $meta[ $name ]['styleVariations'] ?? array(),
		'states'          => $meta[ $name ]['states'] ?? array(),
		'supports'        => $bt->supports,
		'defaults'        => $defaults,
		'dynamic'         => is_callable( $bt->render_callback ),
		'styleHandles'    => $bt->style_handles,
		'usesContext'     => $bt->uses_context,
		'providesContext' => $bt->provides_context,
	);
}
file_put_contents( "$out/blocks.json", svr_json( $blocks ) );

$theme = wp_get_theme();
file_put_contents( "$out/wp-version.txt", 'WordPress ' . get_bloginfo( 'version' ) . "\n" . $theme->get( 'Name' ) . ' ' . $theme->get( 'Version' ) . "\n" );
echo "ok: " . count( $blocks ) . " blocks\n";
