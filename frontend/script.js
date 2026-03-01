const API_URL = 'http://localhost:5001';

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const controlsPanel = document.getElementById('controls-panel');
const resultPanel = document.getElementById('result-panel');
const imagePreview = document.getElementById('image-preview');
const fileNameDisplay = document.getElementById('file-name');
const fileSizeOld = document.getElementById('file-size-old');
const compressBtn = document.getElementById('compress-btn');
const downloadLink = document.getElementById('download-link');
const resetBtn = document.getElementById('reset-btn');

const finalOldSize = document.getElementById('final-old-size');
const finalNewSize = document.getElementById('final-new-size');
const savingBadge = document.getElementById('saving-badge');

let selectedFile = null;

// Event Listeners
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('active');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('active');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('active');
    handleFile(e.dataTransfer.files[0]);
});

fileInput.addEventListener('change', (e) => {
    handleFile(e.target.files[0]);
});

compressBtn.addEventListener('click', compressImage);

resetBtn.addEventListener('click', () => {
    location.reload();
});

// Functions
async function handleFile(file) {
    if (!file) return;

    // Check if it's an image or HEIC/HEIF (browsers often don't label HEIC as image/)
    const isHeic = file.name.toLowerCase().endsWith('.heic') || file.name.toLowerCase().endsWith('.heif');
    if (!file.type.startsWith('image/') && !isHeic) {
        alert('Please drop an image file.');
        return;
    }

    selectedFile = file;
    fileNameDisplay.textContent = file.name;
    fileSizeOld.textContent = formatBytes(file.size);

    // UI state
    dropZone.style.display = 'none';
    controlsPanel.style.display = 'block';

    if (isHeic) {
        // Most browsers can't display HEIC natively
        imagePreview.style.opacity = '0.5';

        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await fetch(`${API_URL}/thumbnail`, {
                method: 'POST',
                body: formData
            });
            if (response.ok) {
                const blob = await response.blob();
                imagePreview.src = URL.createObjectURL(blob);
            } else {
                imagePreview.src = 'https://via.placeholder.com/400x300?text=HEIC+No+Preview';
            }
        } catch (e) {
            imagePreview.src = 'https://via.placeholder.com/400x300?text=Preview+Error';
        }
        imagePreview.style.opacity = '1';
    } else {
        // Normal images
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

async function compressImage() {
    if (!selectedFile) return;

    // Show loading state
    compressBtn.disabled = true;
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');

    btnText.style.display = 'none';
    loader.style.display = 'block';

    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
        const response = await fetch(`${API_URL}/compress`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Optimization failed on server.');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        // Setup download link
        downloadLink.href = url;
        const newFileName = selectedFile.name.substring(0, selectedFile.name.lastIndexOf('.')) + '.avif';
        downloadLink.setAttribute('download', newFileName);

        // Show result stats
        finalOldSize.textContent = formatBytes(selectedFile.size);
        finalNewSize.textContent = formatBytes(blob.size);

        const saving = Math.round(((selectedFile.size - blob.size) / selectedFile.size) * 100);
        savingBadge.textContent = saving > 0 ? `-${saving}%` : `+${Math.abs(saving)}%`;
        if (saving <= 0) savingBadge.style.background = '#4facfe'; // Different color if it grew (rare but possible with skip logic)

        controlsPanel.style.display = 'none';
        resultPanel.style.display = 'block';

    } catch (error) {
        console.error(error);
        alert(error.message);
    } finally {
        compressBtn.disabled = false;
        btnText.style.display = 'block';
        loader.style.display = 'none';
    }
}

function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
