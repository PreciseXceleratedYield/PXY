# PXY installable app — iPhone and macOS

The WebPXY dashboard is installable at `/web/webpxy.html` using its web manifest. The service worker intentionally does **not** cache live data, API responses, authentication, or orders. The app requires a network connection.

## Private remote access (recommended)

**Do not** forward port 80/8080 from your router or publish this Node.js trading server through a public tunnel. The existing server exposes sensitive monitoring APIs, WebSockets, and a trading command route protected by a weak hard-coded action password. A PWA does not itself add authentication.

1. Install Tailscale on the computer hosting the PXY web server, and on the iPhone and Mac. Sign in to the same private tailnet with MFA.
2. Ensure the PXY web server is accessible locally on its configured port. Use Tailscale Serve (private tailnet HTTPS, **not Funnel**) to proxy to that local port. Consult `tailscale serve --help` for the exact command supported by your installed Tailscale version.
3. Confirm the resulting `https://<machine>.<tailnet>.ts.net/web/webpxy.html` URL is reachable from iPhone mobile data with Tailscale connected.
4. iPhone: open that HTTPS URL in Safari, Share → Add to Home Screen → Open as Web App.
5. Mac (macOS Sonoma 14+): open the same URL in Safari, File → Add to Dock.

## Security before trading remotely

- Replace the existing hard-coded action password `1` with robust server-side authentication, with authorization and CSRF protection on every state-changing route. Until then, treat remote access as **monitoring only**, not secure remote trade execution.
- Restrict tailnet access to the intended devices/users and enable MFA. Do not use Tailscale Funnel.
- Verify all HTTP and WebSocket endpoints work over HTTPS/WSS through the private proxy.
- Test the install, reconnect, stale-data indicators, and mobile viewport before relying on the app.
- The service worker uses no fetch handler: no trading data is cached for offline display.

This commit adds installability only; it does not deploy a VPN, create accounts, or validate a live server.
