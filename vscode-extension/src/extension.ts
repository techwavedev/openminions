import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('Openminions Visual Squad Builder is now active!');

    let disposable = vscode.commands.registerCommand('openminions.startBuilder', () => {
        // Create and show a new webview panel
        const panel = vscode.window.createWebviewPanel(
            'openminionsBuilder', // Identifies the type of the webview
            'Openminions Squad Builder', // Title of the panel displayed to the user
            vscode.ViewColumn.One, // Editor column to show the new webview panel in.
            {
                enableScripts: true
            }
        );

        // Set the webview's initial HTML content
        panel.webview.html = getWebviewContent(panel, context);
    });

    context.subscriptions.push(disposable);
}

function getWebviewContent(panel: vscode.WebviewPanel, context: vscode.ExtensionContext) {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Openminions Builder</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            background-color: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }
        .header { margin-bottom: 20px; }
        .canvas {
            width: 100vw;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    </style>
    <link rel="stylesheet" href="${panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'out', 'webview.css'))}" />
</head>
<body>
    <div id="root" class="canvas"></div>
    <script src="${panel.webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'out', 'webview.js'))}"></script>
</body>
</html>`;
}

export function deactivate() {}
