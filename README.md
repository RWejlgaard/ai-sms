# ai-sms

[ai-cli](https://github.com/rwejlgaard/ai-cli)

ChatGPT is finally available over SMS!

Available now in UK on `+44 7763 269816`

## Why?

There's still a lot of people in the world who doesn't have access to a smartphone.

Or if people want to use ChatGPT without all the telemetry and having to download an app.

## How to use

Send a text message _(SMS only, not iMessage)_ to the number above, wait a few seconds and receive your response.

### Commands

|Command|Action|
|---|---|
|`/clear`|Removes rows with the senders phone number from the DB. This clears the conversation history|
|`/system <message>`|Sets the system prompt for the senders phone number. This also clears conversation history|
|`/help`|Sends an SMS with these commands|

## Hosting

The project is running on a Raspberry Pi 4 residing in my rack.

The Pi is wearing two hats. Bottom one is for power-over-ethernet, top one is the "R800C GSM/GPRS HAT" from Waveshare.

I found that GSM signals are not great from within a rack cabinet surrounded by other machines and networking equipment. So it lives slightly outside the rack until I acquire an extension for the antenna to be outside the rack.

![pi in rack wearing two hats](.img/pi-with-hats.jpg)