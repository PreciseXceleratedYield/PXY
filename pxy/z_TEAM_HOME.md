# Team@Home

Team@Home is a private family posts page served by the existing Node.js app at
`/team-at-home`. Posts are stored in a JSON file outside the public `web`
directory, so they are not available from the static-file route.

For this test-machine version, the shared password is hard-coded as `1` in
`teamhome.js`; no environment setup is required. This is intentionally weak
and must not be used on a public or production server. The posts file defaults
to `$PXY_HOME/.pxy/team-home-posts.json` (or the current user's home directory
when `PXY_HOME` is unset). Set `TEAM_HOME_DATA_FILE` to choose another
persistent file location.

The page holds the password only in memory while signed in, and the API limits
repeated incorrect password attempts. Posts show the author's display name and
time; the newest 500 posts are retained. Since this test setup may be accessed
over plain HTTP and uses a known password, use it only on a trusted network.

Run the storage/password checks with:

```sh
node --test pxy/test_teamhome.js
```
