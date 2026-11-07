Copy icon assets to pxy/web/mbl/ and replace pxy/web/mbl/manifest.json with supplied manifest.json.
In pxy/web/webpxy.html replace the existing SVG icon lines with:
<link rel="icon" type="image/png" sizes="32x32" href="/web/mbl/favicon-32.png">
<link rel="shortcut icon" href="/web/mbl/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/web/mbl/apple-touch-icon.png">
Keep the existing manifest link and other PWA metadata unchanged.
