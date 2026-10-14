# Team@Home

Team@Home is a private family posts page served by the existing Node.js app at
`/team-at-home`. Posts are stored in a JSON file outside the public `web`
directory, so they are not available from the static-file route.

Before starting the Node.js server, configure `TEAM_HOME_PASSWORD` in its
server-side environment with a unique password of at least 16 characters. Do
not put the password in this repository, a URL, or the web page source. The
posts file defaults to `$PXY_HOME/.pxy/team-home-posts.json` (or the current
user's home directory when `PXY_HOME` is unset). Set `TEAM_HOME_DATA_FILE` to
choose another persistent file location.

The app must be reached over HTTPS for shared family use. The page holds the
password only in memory while signed in, and the API limits repeated incorrect
password attempts. Posts show the author's display name and time; the newest
500 posts are retained.

Run the storage/password checks with:

```sh
node --test pxy/test_teamhome.js
```
