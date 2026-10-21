<?php
// Применяет пакет redesign/deploy/manifest.json к ЛОКАЛЬНОМУ стенду (redesign/tmp/wp) теми же REST-маршрутами,
// что и на сайте, затем читает всё обратно (context=edit) и сверяет с файлами пакета байт в байт.
// Запуск: php tools/apply_manifest.php [путь к deploy/]   (сайт не трогается: wp-load локальной копии)
$R = dirname( __DIR__ );
$D = rtrim( $argv[1] ?? "$R/deploy", '/' );
require $R . '/tmp/wp/core/wp-load.php';
wp_set_current_user( 1 );
$manifest = json_decode( file_get_contents( "$D/manifest.json" ), true );
$fail = 0;
$made = array();

function rest( $method, $route, $body = null, $params = array() ) {
  $req = new WP_REST_Request( $method, $route );
  foreach ( $params as $k => $v ) { $req->set_param( $k, $v ); }
  if ( null !== $body ) {
    $req->set_header( 'Content-Type', 'application/json' );
    $req->set_body( wp_json_encode( $body ) );
  }
  return rest_do_request( $req );
}
function out( $st, $what, $extra = '' ) { echo str_pad( $st, 5 ) . $what . ( $extra ? "  $extra" : '' ) . "\n"; }

// На сайте пост глобальных стилей — 6, на стенде — свой id.
$local_gs = WP_Theme_JSON_Resolver::get_user_global_styles_post_id();

foreach ( $manifest as $s ) {
  $route = $s['route'];
  $file = isset( $s['file'] ) ? file_get_contents( "$D/{$s['file']}" ) : null;
  switch ( $s['kind'] ) {
    case 'global-styles':
      $route = preg_replace( '#/global-styles/\d+$#', "/global-styles/$local_gs", $route );
      $res = rest( 'POST', $route, json_decode( $file, true ) );
      break;
    case 'template-part':
    case 'template':
      if ( ! empty( $s['create'] ) ) {
        $exists = rest( 'GET', $s['update_route'], null, array( 'context' => 'edit' ) )->get_status() === 200;
        $res = $exists ? rest( 'POST', $s['update_route'], array( 'content' => $file ) )
                       : rest( 'POST', $route, array( 'slug' => $s['slug'], 'title' => $s['title'], 'content' => $file ) );
        $route .= $exists ? ' (exists → ' . $s['update_route'] . ')' : ' (create)';
      } else {
        $res = rest( 'POST', $route, array( 'content' => $file ) );
      }
      break;
    case 'media-alt':
      $res = rest( 'POST', $route, array( 'alt_text' => $s['alt_text'] ) );
      break;
    case 'page':
      $res = rest( 'POST', $route, array( 'content' => $file, 'template' => $s['template'] ) );
      break;
    case 'page-create':
      // страница продукции: если страница с этим адресом (parent/slug) уже есть — обновляем, иначе создаём
      $ex = get_page_by_path( 'prod/' . $s['slug'] );
      $body = array( 'title' => $s['title'], 'slug' => $s['slug'], 'parent' => $s['parent'], 'status' => $s['status'],
                     'comment_status' => $s['comment_status'], 'template' => $s['template'], 'content' => $file );
      $res = $ex ? rest( 'POST', "/wp/v2/pages/{$ex->ID}", $body ) : rest( 'POST', '/wp/v2/pages', $body );
      $route = $ex ? "/wp/v2/pages/{$ex->ID} (update)" : '/wp/v2/pages (create)';
      if ( $res->get_status() < 300 ) { $made[ $s['slug'] ] = $res->get_data()['id']; }
      break;
    default:
      out( 'SKIP', $s['kind'] ); continue 2;
  }
  $st = $res->get_status();
  $fail += $st >= 300;
  out( $st, "{$s['step']}. {$s['kind']} $route", $st >= 300 ? wp_json_encode( $res->get_data() ) : '' );
}

echo "\n== Сверка: GET context=edit против файлов пакета ==\n";
foreach ( $manifest as $s ) {
  $file = isset( $s['file'] ) ? file_get_contents( "$D/{$s['file']}" ) : null;
  $ok = false; $note = '';
  switch ( $s['kind'] ) {
    case 'global-styles':
      $got = rest( 'GET', "/wp/v2/global-styles/$local_gs", null, array( 'context' => 'edit' ) )->get_data();
      $sent = json_decode( $file, true );
      $ok = ( $got['styles']['css'] ?? null ) === $sent['styles']['css'];
      $note = 'styles.css ' . ( $ok ? 'совпадает' : 'ОТЛИЧАЕТСЯ' ) . ' (полный roundtrip — tools/gs_roundtrip.php)';
      break;
    case 'template-part':
    case 'template':
      $r = empty( $s['create'] ) ? $s['route'] : $s['update_route'];
      $got = rest( 'GET', $r, null, array( 'context' => 'edit' ) )->get_data();
      $raw = is_array( $got['content'] ?? null ) ? $got['content']['raw'] : ( $got['content'] ?? '' );
      $ok = trim( $raw ) === trim( $file );
      $note = ( $got['source'] ?? '' ) . ' ' . strlen( $raw ) . ' B';
      break;
    case 'media-alt':
      $got = rest( 'GET', $s['route'], null, array( 'context' => 'edit' ) )->get_data();
      $ok = ( $got['alt_text'] ?? '' ) === $s['alt_text'];
      $note = $got['alt_text'] ?? '';
      break;
    case 'page':
      $got = rest( 'GET', $s['route'], null, array( 'context' => 'edit' ) )->get_data();
      $ok = trim( $got['content']['raw'] ) === trim( $file ) && ( $got['template'] ?? '' ) === $s['template'];
      $note = 'template=' . ( $got['template'] ?: '(page)' ) . ' ' . strlen( $got['content']['raw'] ) . ' B';
      break;
    case 'page-create':
      $id = $made[ $s['slug'] ] ?? 0;
      $got = $id ? rest( 'GET', "/wp/v2/pages/$id", null, array( 'context' => 'edit' ) )->get_data() : array();
      $ok = $id && trim( $got['content']['raw'] ) === trim( $file ) && ( $got['template'] ?? '' ) === $s['template']
            && (int) $got['parent'] === (int) $s['parent'] && $got['status'] === 'publish' && $got['comment_status'] === 'closed'
            && rtrim( $got['link'], '/' ) === rtrim( $s['url'], '/' );
      $note = "id=$id parent={$got['parent']} template={$got['template']} link={$got['link']} " . strlen( $got['content']['raw'] ?? '' ) . ' B';
      break;
  }
  $fail += ! $ok;
  out( $ok ? 'OK' : 'DIFF', "{$s['step']}. {$s['kind']} " . ( $s['file'] ?? $s['route'] ), $note );
}
exit( $fail ? 1 : 0 );
