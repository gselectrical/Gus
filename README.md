# Gus

Internal tools for GS Electrical.

## Hikvision admin reset-code generator

`reset-code-generator.html` is a self-contained, offline tool for recovering a
**forgotten admin password** on Hikvision cameras and NVRs during service work —
without having to email Hikvision support for a code each time.

Open the file in any browser (double-click it, or host it on an internal/local
machine). It runs entirely client-side: nothing is uploaded anywhere.

### How it works

The tool reproduces Hikvision's legacy offline reset: it computes a reset code
from the device's **serial number** and the device's **own clock date**. You
then enter that code in the Hikvision **SADP** tool on the local network to
reset the admin password.

### Authorised use

Use this only on devices you own or are contracted to service, with the owner's
permission. It requires:

- local network access to the device, and
- the SADP tool, and
- the device serial number and the date on the device's internal clock.

It does **not** provide remote access and does nothing on its own — it only
generates the code you type into SADP against a device you can already reach
locally.

### Steps

1. Find the device in the Hikvision SADP tool.
2. Read its serial number and its **Start Time** date (power-cycle the device
   first, let it boot, then refresh SADP — the camera's clock is usually not
   today's date).
3. Enter the serial and that date into the tool and copy the generated code.
4. In SADP, paste it into the **Serial code** / **Security code** field and apply.
5. The default password after reset is typically `123456789abc` — change it
   immediately.

For newer firmware that only accepts an `encrypt.xml` challenge file, use the
manufacturer's official support channel instead.

## Site prep sheet (batch + checklist)

`site-prep.html` is the "prep ahead of the job" version. Same offline engine,
but for a whole list of cameras at once:

- **Batch reset codes** — add a row per camera (location, serial, clock date)
  and each row shows its reset code live, so you can arrive with codes ready.
- **Per-camera setup / handover checklist** — password set, activation,
  IP/network, time & NTP, recording, motion/smart events, Hik-Connect,
  firmware, labelling, client handover — plus a notes box per camera.

It runs fully offline. Your list is saved in the browser on that machine
(localStorage), so you can build it the night before and it'll still be there
on the day. Buttons let you **Print / Save as PDF** (a clean sheet to take on
site) and **Export / Import** the list as a `.json` file to move between
machines or keep a record.

> The reset codes still have to be applied on site via SADP on the device's
> local network, and the camera's clock date must match — confirm it in SADP's
> **Start Time** on the day. This sheet is prep and record-keeping; it does not
> reach any camera itself.
