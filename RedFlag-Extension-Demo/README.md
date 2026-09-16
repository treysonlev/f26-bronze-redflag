# RedFlag browser-extension demo

RedFlag is a functional Chrome/Edge extension prototype that scans visible webpage text, highlights claims covered by its demo rules, and displays a Grammarly-style floating review panel.

## Install locally

1. Download and unzip the project.
2. Open `chrome://extensions` in Google Chrome or `edge://extensions` in Microsoft Edge.
3. Turn on **Developer mode**.
4. Choose **Load unpacked** and select the unzipped `redflag-extension` folder.
5. Pin RedFlag from the browser's Extensions menu.
6. Open `demo.html` or a normal website and select **Scan this page now** from the RedFlag popup.

If you open `demo.html`, enable **Allow access to file URLs** in the extension's Details page.

## What the demo proves

- It runs automatically across normal webpages, including dynamically loaded feeds.
- It highlights matched claims directly where they appear.
- The floating red-flag control reports the number of findings and explains each warning.
- The toolbar popup can turn protection on/off and trigger a fresh scan.
- Settings apply across browser sessions.

## Important limitation

This prototype uses a small, transparent set of known-claim and warning-language rules. It does not determine the truth of every statement. A production version should send extracted claims to a retrieval and verification service, compare them with reliable primary sources and fact-check databases, return citations, and use careful confidence labels. Browser extensions can inspect permitted webpages, but scanning unrelated desktop apps would require a separately installed native desktop application and operating-system screen-access permission.

## Suggested live demonstration

1. Show an ordinary page with no matches: the badge remains clear.
2. Open `demo.html`: three phrases become underlined and marked with red flags.
3. Select the floating **RedFlag** button to explain the warnings.
4. Turn Protection off in the toolbar popup to remove every highlight.
5. Turn it back on to demonstrate continuous background scanning.
