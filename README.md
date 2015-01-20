# web_tunnel

Very simple HTTP Tunnel.  Useful for quick debugging of http requests.
Also supports replacing host header so this can function as a poor man's web debugging tool.

## Example usage

> python web_tunnel.py -p 8888 myapi.internal 8080

With host name replacement (tricking test server into believing it's production)

> python web_tunnel.py -p 8888 -r api.example.com myapi.internal 80

In both cases you can now connect to localhost:8888 and talk to myapi.internal server.  If you want to see the content of the requests and responses add '-vv' argument.

## Advanced usage

If you need to trick the client into using a different hostname then set the tunnel to be the default SOCKS proxy.  Note that only your site will work (for now at least).




