# Security

MacMessageMerge is designed to run only on the user's Mac and binds the web server to `127.0.0.1`.

## Privacy design

- Contact lists are kept in the browser session and are not saved by the app.
- Uploaded CSV files are parsed in memory and are not written to disk.
- Message bodies are not written to the application log.
- Logs contain only operational information such as masked phone numbers and message length.
- The app does not make outbound HTTP requests.

## Required macOS permissions

The app needs Accessibility permission to control the Messages UI and may need Automation permission to control Messages/System Events. Only grant these permissions if you trust the copy of the source you are running.

## Reporting a vulnerability

Please open a GitHub issue without including personal contact data, message contents, screenshots containing phone numbers, or other sensitive information. For a private report, configure a repository security advisory after publishing the repository.
