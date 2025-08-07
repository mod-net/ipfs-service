// IPFS Storage System - Web Interface JavaScript

class IPFSStorageUI {
    constructor() {
        this.currentPage = 0;
        this.pageSize = 12;
        this.currentSearch = '';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFiles();
        this.checkSystemStatus();
    }

    setupEventListeners() {
        // File upload
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');

        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        uploadArea.addEventListener('drop', (e) => this.handleFileDrop(e));
        uploadArea.addEventListener('click', () => fileInput.click());

        // Search
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchFiles();
            }
        });

        // Modal close
        window.addEventListener('click', (e) => {
            const modal = document.getElementById('fileModal');
            if (e.target === modal) {
                this.closeModal();
            }
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadArea').classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadArea').classList.remove('dragover');
    }

    handleFileDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('uploadArea').classList.remove('dragover');

        const files = e.dataTransfer.files;
        this.uploadFiles(files);
    }

    handleFileSelect(e) {
        const files = e.target.files;
        this.uploadFiles(files);
    }

    async uploadFiles(files) {
        if (files.length === 0) return;

        const description = document.getElementById('description').value;
        const tags = document.getElementById('tags').value;

        for (let i = 0; i < files.length; i++) {
            await this.uploadFile(files[i], description, tags);
        }

        // Clear form
        document.getElementById('description').value = '';
        document.getElementById('tags').value = '';
        document.getElementById('fileInput').value = '';

        // Reload files
        this.loadFiles();
    }

    async uploadFile(file, description, tags) {
        const progressDiv = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        progressDiv.style.display = 'block';
        progressText.textContent = `Uploading ${file.name}...`;

        try {
            const formData = new FormData();
            formData.append('file', file);
            if (description) formData.append('description', description);
            if (tags) formData.append('tags', tags);

            const response = await fetch('/api/files/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();
            progressFill.style.width = '100%';
            progressText.textContent = 'Upload complete!';

            this.showToast(`File "${file.name}" uploaded successfully!`, 'success');

            setTimeout(() => {
                progressDiv.style.display = 'none';
                progressFill.style.width = '0%';
            }, 2000);

        } catch (error) {
            progressDiv.style.display = 'none';
            progressFill.style.width = '0%';
            this.showToast(`Upload failed: ${error.message}`, 'error');
        }
    }

    async loadFiles(page = 0) {
        this.currentPage = page;
        const loading = document.getElementById('loading');
        const filesGrid = document.getElementById('filesGrid');

        loading.style.display = 'block';
        filesGrid.innerHTML = '<div class="loading" id="loading"><i class="fas fa-spinner fa-spin"></i> Loading files...</div>';

        try {
            const skip = page * this.pageSize;
            const url = this.currentSearch
                ? '/api/files/search'
                : `/api/files/?skip=${skip}&limit=${this.pageSize}`;

            let response;
            if (this.currentSearch) {
                response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: this.currentSearch,
                        skip: skip,
                        limit: this.pageSize
                    })
                });
            } else {
                response = await fetch(url);
            }

            if (!response.ok) {
                throw new Error('Failed to load files');
            }

            const data = await response.json();
            this.renderFiles(data.files);
            this.updatePagination(data.total, page);
            this.updateStats(data.total);

        } catch (error) {
            filesGrid.innerHTML = `<div class="loading">Error loading files: ${error.message}</div>`;
            this.showToast(`Failed to load files: ${error.message}`, 'error');
        }
    }

    renderFiles(files) {
        const filesGrid = document.getElementById('filesGrid');

        if (files.length === 0) {
            filesGrid.innerHTML = '<div class="loading">No files found</div>';
            return;
        }

        filesGrid.innerHTML = files.map(file => this.createFileCard(file)).join('');
    }

    createFileCard(file) {
        const fileIcon = this.getFileIcon(file.content_type, file.filename);
        const fileSize = this.formatFileSize(file.size);
        const uploadDate = new Date(file.upload_date).toLocaleDateString();
        const tags = file.tags ? JSON.parse(file.tags) : [];

        return `
            <div class="file-card" onclick="ui.showFileDetails('${file.cid}')">
                <div class="file-header">
                    <i class="fas ${fileIcon.icon} file-icon ${fileIcon.class}"></i>
                    <div class="file-info">
                        <h4>${this.escapeHtml(file.filename)}</h4>
                        <div class="file-meta">${fileSize} • ${uploadDate}</div>
                    </div>
                </div>
                <div class="file-details">
                    ${file.description ? `<p><strong>Description:</strong> ${this.escapeHtml(file.description)}</p>` : ''}
                    ${tags.length > 0 ? `<p><strong>Tags:</strong> ${tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join(', ')}</p>` : ''}
                    <p><strong>CID:</strong> <code>${file.cid.substring(0, 20)}...</code></p>
                </div>
                <div class="file-actions">
                    <button class="btn btn-primary" onclick="event.stopPropagation(); ui.downloadFile('${file.cid}', '${file.filename}')">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn btn-secondary" onclick="event.stopPropagation(); ui.copyLink('${file.gateway_url}')">
                        <i class="fas fa-link"></i>
                    </button>
                    <button class="btn btn-danger" onclick="event.stopPropagation(); ui.deleteFile('${file.cid}', '${file.filename}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    getFileIcon(contentType, filename) {
        const ext = filename.split('.').pop().toLowerCase();

        if (contentType && contentType.startsWith('image/')) {
            return { icon: 'fa-image', class: 'image' };
        } else if (contentType && contentType.startsWith('video/')) {
            return { icon: 'fa-video', class: 'video' };
        } else if (contentType && contentType.startsWith('audio/')) {
            return { icon: 'fa-music', class: 'audio' };
        } else if (ext === 'pdf') {
            return { icon: 'fa-file-pdf', class: 'pdf' };
        } else if (['doc', 'docx'].includes(ext)) {
            return { icon: 'fa-file-word', class: 'doc' };
        } else if (['zip', 'tar', 'gz', 'rar'].includes(ext)) {
            return { icon: 'fa-file-archive', class: 'archive' };
        } else if (['txt', 'md'].includes(ext)) {
            return { icon: 'fa-file-text', class: 'text' };
        } else {
            return { icon: 'fa-file', class: 'default' };
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async showFileDetails(cid) {
        try {
            const response = await fetch(`/api/files/${cid}/info`);
            if (!response.ok) {
                throw new Error('Failed to load file details');
            }

            const file = await response.json();
            const modal = document.getElementById('fileModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.getElementById('modalBody');
            const downloadBtn = document.getElementById('downloadBtn');

            modalTitle.textContent = file.filename;
            downloadBtn.onclick = () => this.downloadFile(file.cid, file.filename);

            const tags = file.tags ? JSON.parse(file.tags) : [];

            modalBody.innerHTML = `
                <div class="file-details-modal">
                    <p><strong>Filename:</strong> ${this.escapeHtml(file.filename)}</p>
                    <p><strong>Original Name:</strong> ${this.escapeHtml(file.original_filename)}</p>
                    <p><strong>Size:</strong> ${this.formatFileSize(file.size)}</p>
                    <p><strong>Content Type:</strong> ${file.content_type || 'Unknown'}</p>
                    <p><strong>Upload Date:</strong> ${new Date(file.upload_date).toLocaleString()}</p>
                    <p><strong>CID:</strong> <code>${file.cid}</code></p>
                    ${file.description ? `<p><strong>Description:</strong> ${this.escapeHtml(file.description)}</p>` : ''}
                    ${tags.length > 0 ? `<p><strong>Tags:</strong> ${tags.map(tag => this.escapeHtml(tag)).join(', ')}</p>` : ''}
                    <p><strong>Pinned:</strong> ${file.is_pinned ? 'Yes' : 'No'}</p>
                    <p><strong>Gateway URL:</strong> <a href="${file.gateway_url}" target="_blank">${file.gateway_url}</a></p>
                </div>
            `;

            modal.style.display = 'block';

        } catch (error) {
            this.showToast(`Failed to load file details: ${error.message}`, 'error');
        }
    }

    closeModal() {
        document.getElementById('fileModal').style.display = 'none';
    }

    async downloadFile(cid, filename) {
        try {
            const response = await fetch(`/api/files/${cid}`);
            if (!response.ok) {
                throw new Error('Download failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            this.showToast(`Downloaded ${filename}`, 'success');

        } catch (error) {
            this.showToast(`Download failed: ${error.message}`, 'error');
        }
    }

    async copyLink(url) {
        try {
            await navigator.clipboard.writeText(url);
            this.showToast('Link copied to clipboard!', 'success');
        } catch (error) {
            this.showToast('Failed to copy link', 'error');
        }
    }

    async deleteFile(cid, filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/files/${cid}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Delete failed');
            }

            this.showToast(`Deleted ${filename}`, 'success');
            this.loadFiles(this.currentPage);

        } catch (error) {
            this.showToast(`Delete failed: ${error.message}`, 'error');
        }
    }

    async searchFiles() {
        const query = document.getElementById('searchInput').value.trim();
        this.currentSearch = query;
        this.currentPage = 0;
        await this.loadFiles(0);
    }

    updatePagination(total, currentPage) {
        const pagination = document.getElementById('pagination');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const pageInfo = document.getElementById('pageInfo');

        const totalPages = Math.ceil(total / this.pageSize);

        if (totalPages <= 1) {
            pagination.style.display = 'none';
            return;
        }

        pagination.style.display = 'flex';
        prevBtn.disabled = currentPage === 0;
        nextBtn.disabled = currentPage >= totalPages - 1;
        pageInfo.textContent = `Page ${currentPage + 1} of ${totalPages}`;
    }

    updateStats(total) {
        document.getElementById('totalFiles').textContent = `${total} files`;
    }

    previousPage() {
        if (this.currentPage > 0) {
            this.loadFiles(this.currentPage - 1);
        }
    }

    nextPage() {
        this.loadFiles(this.currentPage + 1);
    }

    async checkSystemStatus() {
        try {
            const response = await fetch('/info');
            const info = await response.json();

            const statusElement = document.getElementById('nodeStatus');
            if (info.status === 'operational') {
                statusElement.innerHTML = `<i class="fas fa-check-circle" style="color: #28a745;"></i> Connected to IPFS node`;
            } else {
                statusElement.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: #ffc107;"></i> IPFS connection issues`;
            }
        } catch (error) {
            document.getElementById('nodeStatus').innerHTML = `<i class="fas fa-times-circle" style="color: #dc3545;"></i> System offline`;
        }
    }

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas ${this.getToastIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    getToastIcon(type) {
        switch (type) {
            case 'success': return 'fa-check-circle';
            case 'error': return 'fa-times-circle';
            case 'warning': return 'fa-exclamation-triangle';
            default: return 'fa-info-circle';
        }
    }
}

// Global functions for HTML onclick handlers
window.searchFiles = () => ui.searchFiles();
window.loadFiles = () => ui.loadFiles();
window.previousPage = () => ui.previousPage();
window.nextPage = () => ui.nextPage();
window.closeModal = () => ui.closeModal();

// Initialize the UI when the page loads
const ui = new IPFSStorageUI();
