@echo off
:loop
echo Starting localtunnel...
npx localtunnel --port 3000 --subdomain shiny-plants-sneeze
echo Tunnel closed, reconnecting in 3 seconds...
timeout /t 3
goto loop
