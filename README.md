# impactP-server
Makes a Technifor impactP part marking machine available over the web via HTTP requests. The purpose was to allow communication with the machine from an ERP web app.

- Uses Flask with Ngrok to provide a URL on the internet to communicate with a computer on the same network as the part marking machine.
- The script maintains a Telnet connection over the local network. When it recieves an HTTP request from the web app, it relays it over Telnet to the machine and then returns the response from the machine as a response to the web app.
