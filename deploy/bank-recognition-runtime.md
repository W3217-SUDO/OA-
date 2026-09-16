# Bank document recognition runtime

Requires the existing LANGGRAPH_API_BASE_URL, LANGGRAPH_API_KEY and LANGGRAPH_MODEL
configuration to point to a model that accepts chat/completions text and image content.
Do not log credentials or document contents. These settings are read from the API
service environment, not copied into the repository.

OpenCloudOS Word conversion dependency:

```sh
dnf install -y libreoffice-writer libreoffice-langpack-zh-Hans
libreoffice --headless --version
```

Windows local development: install LibreOffice and put its program directory on PATH.
PDF rendering uses the existing pinned pypdfium2 dependency; image reading uses Pillow.
No database migration is required. Rolling back the application does not require
removing LibreOffice; it does not run as a persistent service.

Limits: 100 MiB upload, 20 pages/frames per document, 120,000 text characters,
25 million pixels per source image, 1,000 recognized records, ZIP at most 10 supported
files / 100 MiB expanded. Nested/encrypted archives are rejected. No partial page
truncation. Model processing has a 480-second overall timeout and is serialized per
API worker. Word conversion has a 90-second timeout and isolated temporary profile.

Recognized documents always return a non-persistent preview. Confirmations are
signed for 30 minutes and bound to the user, bank and complete result digest.
Final import revalidates permissions, fields and duplicate references. Temporary
source/conversion files are removed on completion or failure.
