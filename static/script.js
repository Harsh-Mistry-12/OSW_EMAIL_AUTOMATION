// OSW Email Automation Dashboard Script

document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation ---
    const navButtons = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.content-section');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const sectionTarget = btn.getAttribute('data-section');

            // Toggle buttons
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle sections
            sections.forEach(s => s.classList.remove('active'));
            document.getElementById(sectionTarget).classList.add('active');

            // Specific logic when switching
            if (sectionTarget === 'template-section') loadTemplates();
            if (sectionTarget === 'preview-section') setupPreview();
        });
    });

    // --- CSV Upload ---
    const dropZone = document.getElementById('csv-drop-zone');
    const csvInput = document.getElementById('csv-input');
    let loadedRecipients = [];

    dropZone.addEventListener('click', () => csvInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragging');
    });

    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragging'));

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragging');
        const files = e.dataTransfer.files;
        if (files.length) handleCSVUpload(files[0]);
    });

    csvInput.addEventListener('change', () => {
        if (csvInput.files.length) handleCSVUpload(csvInput.files[0]);
    });

    async function handleCSVUpload(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch('/api/upload-csv', { method: 'POST', body: formData });
            const data = await resp.json();

            if (data.error) throw new Error(data.error);

            showToast('CSV uploaded successfully!');
            renderCSVPreview(data);
            loadedRecipients = data.preview;
            document.getElementById('summary-recipients').innerText = data.preview.length + "+";
        } catch (err) {
            alert('Upload failed: ' + err.message);
        }
    }

    function renderCSVPreview(data) {
        const container = document.getElementById('csv-preview-container');
        const table = document.getElementById('csv-preview-table');
        container.classList.remove('hidden');

        let html = '<thead><tr>';
        data.columns.slice(0, 5).forEach(col => html += `<th>${col}</th>`);
        html += '</tr></thead><tbody>';

        data.preview.forEach(row => {
            html += '<tr>';
            data.columns.slice(0, 5).forEach(col => html += `<td>${row[col] || ''}</td>`);
            html += '</tr>';
        });

        html += '</tbody>';
        table.innerHTML = html;
    }

    // --- Templates ---
    const templateList = document.getElementById('template-list');
    const editor = document.getElementById('template-editor');
    const placeholdersTags = document.getElementById('placeholder-tags');
    let currentTemplateName = '';

    async function loadTemplates() {
        const resp = await fetch('/api/templates');
        const data = await resp.json();

        templateList.innerHTML = '';
        data.templates.forEach(name => {
            const div = document.createElement('div');
            div.className = 'template-item';
            div.innerText = name;
            div.onclick = () => loadTemplateContent(name);
            templateList.appendChild(div);
        });
    }

    async function loadTemplateContent(name) {
        const resp = await fetch(`/api/template/${name}`);
        const data = await resp.json();

        currentTemplateName = name;
        editor.value = data.content;
        renderPlaceholders(data.placeholders);

        // Update UI
        document.querySelectorAll('.template-item').forEach(item => {
            item.classList.toggle('active', item.innerText === name);
        });
        document.getElementById('editor-title').innerText = `Editing: ${name}`;
        document.getElementById('summary-template').innerText = name;
    }

    function renderPlaceholders(placeholders) {
        placeholdersTags.innerHTML = '';
        placeholders.forEach(p => {
            const span = document.createElement('span');
            span.className = 'tag';
            span.innerText = `{{ ${p} }}`;
            placeholdersTags.appendChild(span);
        });
    }

    document.getElementById('save-template-btn').onclick = async () => {
        const name = currentTemplateName || prompt('Template Name:', 'new_template.html');
        if (!name) return;

        const formData = new FormData();
        formData.append('name', name);
        formData.append('content', editor.value);

        const resp = await fetch('/api/save-template', { method: 'POST', body: formData });
        const result = await resp.json();

        if (result.status === 'success') {
            showToast('Template saved!');
            loadTemplates();
            currentTemplateName = result.name;
        }
    };

    document.getElementById('add-template-btn').onclick = () => {
        currentTemplateName = '';
        editor.value = '<html>\n<body>\n  <h1>Hello {{ recipient_name }}!</h1>\n  <p>Welcome to OSW.</p>\n</body>\n</html>';
        document.getElementById('editor-title').innerText = 'New Template';
        renderPlaceholders(['recipient_name']);
    };

    // --- Preview ---
    const previewDataInputs = document.getElementById('preview-data-inputs');
    const previewFrame = document.getElementById('email-preview-frame');

    function setupPreview() {
        // Detect placeholders from current editor content
        const content = editor.value;
        const matches = [...new Set(content.match(/\{\{\s*(\w+)\s*\}\}/g) || [])];
        const placeholders = matches.map(m => m.replace(/\{\{\s*|\s*\}\}/g, ''));

        previewDataInputs.innerHTML = '';
        placeholders.forEach(p => {
            const div = document.createElement('div');
            div.className = 'input-field';

            // Default sample data
            let val = '';
            if (p.includes('name')) val = 'John Doe';
            if (p.includes('company')) val = 'OSW Corp';
            if (p.includes('bullets')) val = '• Amazing Networking\n• Real-world projects\n• Fun Weekend';

            div.innerHTML = `
                <label>${p}</label>
                ${p.includes('bullets') ? `<textarea data-key="${p}">${val}</textarea>` : `<input type="text" data-key="${p}" value="${val}">`}
            `;
            previewDataInputs.appendChild(div);
        });

        refreshPreview();
    }

    async function refreshPreview() {
        const inputs = previewDataInputs.querySelectorAll('input, textarea');
        const data = {};
        inputs.forEach(input => {
            data[input.getAttribute('data-key')] = input.value;
        });

        const formData = new FormData();
        formData.append('template_content', editor.value);
        formData.append('data', JSON.stringify(data));

        try {
            const resp = await fetch('/api/preview', { method: 'POST', body: formData });
            const result = await resp.json();

            const doc = previewFrame.contentDocument || previewFrame.contentWindow.document;
            doc.open();
            doc.write(result.html);
            doc.close();
        } catch (err) {
            console.error('Preview failed', err);
        }
    }

    document.getElementById('refresh-preview-btn').onclick = refreshPreview;

    // --- Toast & Utils ---
    function showToast(msg) {
        const toast = document.getElementById('toast');
        toast.innerText = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }
});
