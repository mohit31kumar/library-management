document.addEventListener('DOMContentLoaded', () => {
    // --- File Deletion Logic ---
    document.querySelectorAll('.btn-delete').forEach(button => {
        button.addEventListener('click', async (e) => {
            const path = e.target.dataset.path;
            const type = e.target.dataset.type;
            const confirmation = window.confirm(`Are you sure you want to delete this ${type}?`);
            
            if (confirmation) {
                try {
                    const response = await fetch('/delete', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: `path=${encodeURIComponent(path)}`
                    });

                    const result = await response.json();
                    if (result.success) {
                        alert(result.message);
                        location.reload(); // Reload to update file list
                    } else {
                        alert(`Error: ${result.message}`);
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('An error occurred during the request.');
                }
            }
        });
    });

    // --- Terminal Logic ---
    const terminalOutput = document.getElementById('terminal-output');
    const terminalInput = document.getElementById('terminal-input');
    const runCommandBtn = document.getElementById('run-command-btn');

    const runCommand = async () => {
        const command = terminalInput.value;
        if (!command) return;

        terminalOutput.innerHTML += `<p class="terminal-prompt-history">&gt; ${command}</p>`;
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
        terminalInput.value = '';

        try {
            const response = await fetch('/terminal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command: command })
            });

            const result = await response.json();
            
            let outputText = result.output || result.error || '';
            let outputClass = result.success ? '' : 'error';
            
            terminalOutput.innerHTML += `<div class="${outputClass}">${outputText}</div>`;
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
            
        } catch (error) {
            console.error('Error:', error);
            terminalOutput.innerHTML += `<div class="error">An error occurred while running the command.</div>`;
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }
    };
    
    runCommandBtn.addEventListener('click', runCommand);
    terminalInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            runCommand();
        }
    });

    // --- File Upload Form Logic ---
    const uploadForm = document.getElementById('upload-form');
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(uploadForm);
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();
            if (result.success) {
                alert(result.message);
                location.reload(); // Reload to see the new file
            } else {
                alert(`Error: ${result.message}`);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during the upload.');
        }
    });
});