/**
 * PDF Magic Core Logic (Vanilla JS Refactoring)
 * Handles PDF processing, masking, and multi-format export.
 */
class PDFMagic {
    constructor() {
        console.log("[PDF Magic] Initializing Instance...");
        window.pdfMagic = this; // Self-attach
        this.currentPdf = null;
        this.maskRect = null;
        this.isDrawing = false;
        this.startX = 0; 
        this.startY = 0;
        this.selectionCanvas = null;
        this.ctxSel = null;

        // Global results storage
        this.globalZip = null;
        this.globalPdfDoc = null;
        this.globalPptx = null;

        // Give DOM time to settle
        setTimeout(() => this.init(), 100);
    }

    init() {
        console.log("[PDF Magic] Running Init...");
        this.bindEvents();
    }

    get elements() {
        const get = (id) => {
            const el = document.getElementById(id);
            if (!el) console.warn(`[PDF Magic] Missing Element: ${id}`);
            return el;
        };
        return {
            fileInput: get('pdf-file-input'),
            maskEditor: get('pdf-mask-editor'),
            canvasWrapper: get('pdf-canvas-wrapper'),
            convertBtn: get('pdf-convert-btn'),
            progressBar: get('pdf-progress-bar'),
            progressFill: get('pdf-progress-fill'),
            status: get('pdf-status'),
            downloadsArea: get('pdf-downloads-area'),
            previewArea: get('pdf-preview-grid'),
            scaleSelect: get('pdf-scale-select'),
            fillMode: get('pdf-fill-mode'),
            btnZip: get('pdf-btn-zip'),
            btnPdf: get('pdf-btn-pdf'),
            btnPptx: get('pdf-btn-pptx'),
            fileNameDisplay: get('pdf-file-name')
        };
    }

    bindEvents() {
        const el = this.elements;
        if (el.fileInput) {
            el.fileInput.onchange = () => {
                const fileName = el.fileInput.files[0] ? el.fileInput.files[0].name : 'NO FILE SELECTED';
                if (el.fileNameDisplay) el.fileNameDisplay.innerText = fileName.toUpperCase();
                this.loadForPreview();
            };
        }
        if (el.convertBtn) {
            el.convertBtn.onclick = () => this.startProcessing();
        }
    }

    async loadForPreview() {
        const el = this.elements;
        if (!el.fileInput.files.length) return;

        console.log("[PDF Magic] Loading file for preview...");
        el.canvasWrapper.innerHTML = '';
        this.maskRect = null;

        const file = el.fileInput.files[0];
        const arrayBuffer = await file.arrayBuffer();
        
        try {
            this.currentPdf = await pdfjsLib.getDocument(arrayBuffer).promise;
            const page = await this.currentPdf.getPage(1);
            const viewport = page.getViewport({ scale: 1.0 });

            const bgCanvas = document.createElement('canvas');
            bgCanvas.width = viewport.width;
            bgCanvas.height = viewport.height;
            await page.render({ canvasContext: bgCanvas.getContext('2d'), viewport }).promise;

            this.selectionCanvas = document.createElement('canvas');
            this.selectionCanvas.className = 'selection-canvas';
            this.selectionCanvas.width = viewport.width;
            this.selectionCanvas.height = viewport.height;
            this.ctxSel = this.selectionCanvas.getContext('2d');

            this.selectionCanvas.onmousedown = (e) => this.onMouseDown(e);
            this.selectionCanvas.onmousemove = (e) => this.onMouseMove(e);
            this.selectionCanvas.onmouseup = (e) => this.onMouseUp(e);

            el.canvasWrapper.appendChild(bgCanvas);
            el.canvasWrapper.appendChild(this.selectionCanvas);

            el.maskEditor.style.display = 'block';
            el.convertBtn.disabled = false;
            el.status.innerText = `READY. PAGES: ${this.currentPdf.numPages}. SELECT MASK AREA.`;
            el.downloadsArea.style.display = 'none';

        } catch (err) {
            console.error("[PDF Magic] Load error:", err);
            el.status.innerText = "ERROR LOADING PDF.";
        }
    }

    // --- Masking Logic ---
    onMouseDown(e) {
        const r = this.selectionCanvas.getBoundingClientRect();
        this.startX = e.clientX - r.left;
        this.startY = e.clientY - r.top;
        this.isDrawing = true;
    }

    onMouseMove(e) {
        if (!this.isDrawing) return;
        const r = this.selectionCanvas.getBoundingClientRect();
        const curX = e.clientX - r.left;
        const curY = e.clientY - r.top;
        this.drawSelection(this.startX, this.startY, curX - this.startX, curY - this.startY);
    }

    onMouseUp(e) {
        if (!this.isDrawing) return;
        this.isDrawing = false;
        const r = this.selectionCanvas.getBoundingClientRect();
        const endX = e.clientX - r.left;
        const endY = e.clientY - r.top;
        
        const x = Math.min(this.startX, endX);
        const y = Math.min(this.startY, endY);
        const w = Math.abs(endX - this.startX);
        const h = Math.abs(endY - this.startY);

        if (w > 5 && h > 5) {
            this.maskRect = {
                x: x / this.selectionCanvas.width,
                y: y / this.selectionCanvas.height,
                w: w / this.selectionCanvas.width,
                h: h / this.selectionCanvas.height
            };
            this.ctxSel.clearRect(0, 0, this.selectionCanvas.width, this.selectionCanvas.height);
            this.ctxSel.fillStyle = 'rgba(255, 140, 0, 0.4)';
            this.ctxSel.strokeStyle = '#ff8c00';
            this.ctxSel.lineWidth = 2;
            this.ctxSel.strokeRect(x, y, w, h);
            this.ctxSel.fillRect(x, y, w, h);
        }
    }

    drawSelection(x, y, w, h) {
        this.ctxSel.clearRect(0, 0, this.selectionCanvas.width, this.selectionCanvas.height);
        this.ctxSel.fillStyle = 'rgba(255, 140, 0, 0.2)';
        this.ctxSel.fillRect(x, y, w, h);
    }

    resetMask() {
        this.maskRect = null;
        if (this.ctxSel) this.ctxSel.clearRect(0, 0, this.selectionCanvas.width, this.selectionCanvas.height);
    }

    // --- Processing ---
    async startProcessing() {
        if (!this.currentPdf) return;
        const el = this.elements;
        const scale = parseFloat(el.scaleSelect.value);
        const fillMode = el.fillMode.value;
        const baseName = el.fileInput.files[0].name.replace('.pdf', '');

        el.downloadsArea.style.display = 'none';
        el.progressBar.style.display = 'block';
        el.previewArea.innerHTML = '';
        el.convertBtn.disabled = true;

        // Init Libraries
        this.globalZip = new JSZip();
        const imgFolder = this.globalZip.folder(baseName + '_images');
        
        // Use more robust jsPDF access
        const jsPDFLib = window.jspdf ? window.jspdf.jsPDF : window.jsPDF;
        if (!jsPDFLib) {
            alert("PDF Library (jsPDF) not found! Check connection.");
            return;
        }

        // We reset the PDF doc here. We'll init it in the loop to match first page size.
        this.globalPdfDoc = null;

        this.globalPptx = new PptxGenJS();
        this.globalPptx.layout = 'LAYOUT_16x9';

        el.status.innerText = 'INITIALIZING ENGINE...';

        try {
            for (let i = 1; i <= this.currentPdf.numPages; i++) {
                el.status.innerText = `PROCESSING PAGE ${i} / ${this.currentPdf.numPages}...`;
                el.progressFill.style.width = `${((i - 1) / this.currentPdf.numPages) * 100}%`;

                const page = await this.currentPdf.getPage(i);
                const viewport = page.getViewport({ scale: scale });
                const canvas = document.createElement('canvas');
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                const ctx = canvas.getContext('2d');
                await page.render({ canvasContext: ctx, viewport }).promise;

                if (this.maskRect) {
                    const mx = Math.floor(this.maskRect.x * canvas.width);
                    const my = Math.floor(this.maskRect.y * canvas.height);
                    const mw = Math.ceil(this.maskRect.w * canvas.width);
                    const mh = Math.ceil(this.maskRect.h * canvas.height);
                    
                    let col = '#FFFFFF';
                    if (fillMode === 'white') col = '#FFFFFF';
                    else col = this.getAverageColor(ctx, mx, my, mw, mh, fillMode);
                    
                    ctx.fillStyle = col; 
                    ctx.fillRect(mx - 1, my - 1, mw + 2, mh + 2);
                }

                const imgDataUrl = canvas.toDataURL('image/png'); 
                const base64Content = imgDataUrl.split(',')[1];
                imgFolder.file(`page_${String(i).padStart(3, '0')}.png`, base64Content, {base64: true});

                // PDF Logic
                const orientation = canvas.width > canvas.height ? 'landscape' : 'portrait';
                if (i === 1) {
                    this.globalPdfDoc = new jsPDFLib({
                        orientation: orientation,
                        unit: 'px',
                        format: [canvas.width, canvas.height],
                        hotfixes: ["px_scaling"]
                    });
                } else {
                    this.globalPdfDoc.addPage([canvas.width, canvas.height], orientation);
                }
                this.globalPdfDoc.addImage(imgDataUrl, 'PNG', 0, 0, canvas.width, canvas.height, undefined, 'FAST');

                // PPTX Logic
                let slide = this.globalPptx.addSlide();
                slide.addImage({ data: imgDataUrl, x: 0, y: 0, w: '100%', h: '100%', sizing: { type: 'contain', align: 'center' } });

                if (i <= 6) {
                    const div = document.createElement('div');
                    div.className = 'pdf-preview-item ag-card';
                    div.innerHTML = `<img src="${imgDataUrl}"><span>PAGE ${i}</span>`;
                    el.previewArea.appendChild(div);
                }
                canvas.width = 1; // Cleanup hack
            }

            el.progressFill.style.width = '100%';
            el.status.innerText = 'CONVERSION COMPLETE. SELECT EXPORT FORMAT.';
            el.downloadsArea.style.display = 'flex';
            this.setupDownloads(baseName);

        } catch (err) {
            console.error(err);
            el.status.innerText = 'ERROR: ' + err.message;
        } finally {
            el.convertBtn.disabled = false;
        }
    }

    getAverageColor(ctx, x, y, w, h, mode) {
        const s = 6;
        let sx = x, sy = y, sw = s, sh = h;
        if (mode === 'left') { sx = x - s; sy = y; sw = s; sh = h; }
        else if (mode === 'right') { sx = x + w; sy = y; sw = s; sh = h; }
        else if (mode === 'top') { sx = x; sy = y - s; sw = w; sh = s; }
        else if (mode === 'bottom') { sx = x; sy = y + h; sw = w; sh = s; }

        if (sx < 0) sx = 0; if (sy < 0) sy = 0;
        try {
            const d = ctx.getImageData(sx, sy, sw, sh).data;
            let r=0, g=0, b=0, c=0;
            for(let i=0; i<d.length; i+=4){ r+=d[i]; g+=d[i+1]; b+=d[i+2]; c++; }
            return `rgb(${Math.floor(r/c)},${Math.floor(g/c)},${Math.floor(b/c)})`;
        } catch (e) { return '#FFFFFF'; }
    }

    setupDownloads(baseName) {
        const el = this.elements;
        console.log("[PDF Magic] Setting up downloads for:", baseName);
        
        el.btnZip.onclick = async () => {
            console.log("[PDF Magic] ZIP Export requested.");
            el.btnZip.innerText = 'PACKING...';
            try {
                const content = await this.globalZip.generateAsync({type:"blob"});
                this.saveFile(content, `${baseName}_HD.zip`);
            } catch (e) { console.error(e); }
            el.btnZip.innerText = 'ZIP ARCHIVE';
        };

        el.btnPdf.onclick = () => {
            console.log("[PDF Magic] PDF Export requested.");
            if (!this.globalPdfDoc) { alert("PDF Document not generated!"); return; }
            try {
                this.globalPdfDoc.save(`${baseName}_CLEAN.pdf`);
            } catch (e) { 
                console.error("[PDF Magic] PDF Save Error:", e);
                alert("Critical error during PDF save. Check console.");
            }
        };

        el.btnPptx.onclick = () => {
            console.log("[PDF Magic] PPTX Export requested.");
            try {
                this.globalPptx.writeFile({ fileName: `${baseName}_PRESENTATION.pptx` });
            } catch (e) { console.error(e); }
        };
    }

    saveFile(blob, filename) {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
    }
}

// Global initialization
new PDFMagic();
