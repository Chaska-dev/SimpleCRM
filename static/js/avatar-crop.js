let cropState = {
    img: null,
    container: null,
    cropFrame: null,
    cropCircle: null,
    dragMode: null,
    dragStartX: 0,
    dragStartY: 0,
    frameX: 0,
    frameY: 0,
    frameSize: 150,
    startFrameX: 0,
    startFrameY: 0,
    startFrameSize: 0,
    imgWidth: 0,
    imgHeight: 0,
    containerWidth: 0,
    containerHeight: 0,
    imgLeft: 0,
    imgTop: 0,
    activeHandle: null
};

function handleImageSelect(input, previewId, cropXId, cropYId, cropSizeId, uploadUrl, csrfToken) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.getElementById('cropperImage');
            img.src = e.target.result;
            img.onload = function() {
                openCropper(previewId, cropXId, cropYId, cropSizeId, uploadUrl, csrfToken);
            };
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function openCropper(previewId, cropXId, cropYId, cropSizeId, uploadUrl, csrfToken) {
    const modal = document.getElementById('cropperModal');
    const container = document.getElementById('cropperContainer');
    const img = document.getElementById('cropperImage');
    const cropFrame = document.getElementById('cropFrame');
    const cropCircle = document.getElementById('cropCircle');
    
    modal.classList.remove('hidden');
    
    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;
    
    const imgWidth = img.naturalWidth;
    const imgHeight = img.naturalHeight;
    
    const scaleX = containerWidth / imgWidth;
    const scaleY = containerHeight / imgHeight;
    const scale = Math.min(scaleX, scaleY);
    
    const scaledWidth = imgWidth * scale;
    const scaledHeight = imgHeight * scale;
    
    cropState.img = img;
    cropState.container = container;
    cropState.cropFrame = cropFrame;
    cropState.cropCircle = cropCircle;
    cropState.containerWidth = containerWidth;
    cropState.containerHeight = containerHeight;
    cropState.imgWidth = scaledWidth;
    cropState.imgHeight = scaledHeight;
    cropState.scale = scale;
    cropState.previewId = previewId;
    cropState.cropXId = cropXId;
    cropState.cropYId = cropYId;
    cropState.cropSizeId = cropSizeId;
    cropState.uploadUrl = uploadUrl;
    cropState.csrfToken = csrfToken;
    
    cropState.imgLeft = (containerWidth - scaledWidth) / 2;
    cropState.imgTop = (containerHeight - scaledHeight) / 2;
    
    img.style.width = scaledWidth + 'px';
    img.style.height = scaledHeight + 'px';
    img.style.left = cropState.imgLeft + 'px';
    img.style.top = cropState.imgTop + 'px';
    
    cropState.frameX = cropState.imgLeft;
    cropState.frameY = cropState.imgTop;
    cropState.frameSize = Math.min(scaledWidth, scaledHeight) * 0.5;
    cropState.startFrameX = cropState.frameX;
    cropState.startFrameY = cropState.frameY;
    cropState.startFrameSize = cropState.frameSize;
    
    updateCropFramePosition();
    
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('mouseup', endDrag);
    document.addEventListener('touchmove', onDragTouch, {passive: false});
    document.addEventListener('touchend', endDrag);
    
    document.querySelectorAll('.resize-handle').forEach(handle => {
        handle.addEventListener('mousedown', startResize);
        handle.addEventListener('touchstart', startResizeTouch, {passive: false});
    });
    
    cropCircle.addEventListener('mousedown', startMove);
    cropCircle.addEventListener('touchstart', startMoveTouch, {passive: false});
}

function updateCropFramePosition() {
    cropState.cropFrame.style.left = cropState.frameX + 'px';
    cropState.cropFrame.style.top = cropState.frameY + 'px';
    cropState.cropFrame.style.width = cropState.frameSize + 'px';
    cropState.cropFrame.style.height = cropState.frameSize + 'px';
}

function startMove(e) {
    e.preventDefault();
    e.stopPropagation();
    cropState.dragMode = 'move';
    cropState.dragStartX = e.clientX;
    cropState.dragStartY = e.clientY;
    cropState.startFrameX = cropState.frameX;
    cropState.startFrameY = cropState.frameY;
}

function startResize(e) {
    e.preventDefault();
    e.stopPropagation();
    cropState.dragMode = 'resize';
    cropState.dragStartX = e.clientX;
    cropState.dragStartY = e.clientY;
    cropState.activeHandle = e.target.dataset.dir;
    cropState.startFrameX = cropState.frameX;
    cropState.startFrameY = cropState.frameY;
    cropState.startFrameSize = cropState.frameSize;
}

function startMoveTouch(e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.touches.length === 1) {
        cropState.dragMode = 'move';
        cropState.dragStartX = e.touches[0].clientX;
        cropState.dragStartY = e.touches[0].clientY;
        cropState.startFrameX = cropState.frameX;
        cropState.startFrameY = cropState.frameY;
    }
}

function startResizeTouch(e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.touches.length === 1) {
        cropState.dragMode = 'resize';
        cropState.dragStartX = e.touches[0].clientX;
        cropState.dragStartY = e.touches[0].clientY;
        cropState.activeHandle = e.target.dataset.dir;
        cropState.startFrameX = cropState.frameX;
        cropState.startFrameY = cropState.frameY;
        cropState.startFrameSize = cropState.frameSize;
    }
}

function onDrag(e) {
    if (!cropState.dragMode) return;

    const deltaX = e.clientX - cropState.dragStartX;
    const deltaY = e.clientY - cropState.dragStartY;

    if (cropState.dragMode === 'move') {
        let newX = cropState.startFrameX + deltaX;
        let newY = cropState.startFrameY + deltaY;

        newX = Math.max(cropState.imgLeft, Math.min(cropState.imgLeft + cropState.imgWidth - cropState.frameSize, newX));
        newY = Math.max(cropState.imgTop, Math.min(cropState.imgTop + cropState.imgHeight - cropState.frameSize, newY));

        cropState.frameX = newX;
        cropState.frameY = newY;
    } else if (cropState.dragMode === 'resize') {
        const minSize = 60;
        const maxSize = Math.min(cropState.imgWidth, cropState.imgHeight);
        const handle = cropState.activeHandle;

        let newFrameX = cropState.startFrameX;
        let newFrameY = cropState.startFrameY;
        let newFrameSize = cropState.startFrameSize;

        if (handle === 'se') {
            newFrameSize = cropState.startFrameSize + Math.max(deltaX, deltaY);
        } else if (handle === 'nw') {
            const sizeDelta = Math.max(deltaX, deltaY);
            newFrameSize = cropState.startFrameSize - sizeDelta;
            newFrameX = cropState.startFrameX + (cropState.startFrameSize - newFrameSize);
            newFrameY = cropState.startFrameY + (cropState.startFrameSize - newFrameSize);
        } else if (handle === 'ne') {
            newFrameSize = cropState.startFrameSize + Math.max(deltaX, -deltaY);
            newFrameY = cropState.startFrameY - (newFrameSize - cropState.startFrameSize);
        } else if (handle === 'sw') {
            newFrameSize = cropState.startFrameSize + Math.max(-deltaX, deltaY);
            newFrameX = cropState.startFrameX + (cropState.startFrameSize - newFrameSize);
        } else if (handle === 'n') {
            newFrameSize = cropState.startFrameSize - deltaY;
            newFrameY = cropState.startFrameY + deltaY;
        } else if (handle === 's') {
            newFrameSize = cropState.startFrameSize + deltaY;
        } else if (handle === 'w') {
            newFrameSize = cropState.startFrameSize - deltaX;
            newFrameX = cropState.startFrameX + deltaX;
        } else if (handle === 'e') {
            newFrameSize = cropState.startFrameSize + deltaX;
        }

        newFrameSize = Math.max(minSize, Math.min(maxSize, newFrameSize));

        if (handle === 'nw' || handle === 'n' || handle === 'w') {
            const sizeDiff = cropState.startFrameSize - newFrameSize;
            if (handle === 'nw' || handle === 'w') {
                newFrameX = cropState.startFrameX + sizeDiff;
            }
            if (handle === 'nw' || handle === 'n') {
                newFrameY = cropState.startFrameY + sizeDiff;
            }
        }

        newFrameX = Math.max(cropState.imgLeft, newFrameX);
        newFrameY = Math.max(cropState.imgTop, newFrameY);

        if (newFrameX + newFrameSize > cropState.imgLeft + cropState.imgWidth) {
            newFrameSize = cropState.imgLeft + cropState.imgWidth - newFrameX;
        }
        if (newFrameY + newFrameSize > cropState.imgTop + cropState.imgHeight) {
            newFrameSize = cropState.imgTop + cropState.imgHeight - newFrameY;
        }

        cropState.frameX = newFrameX;
        cropState.frameY = newFrameY;
        cropState.frameSize = Math.max(minSize, newFrameSize);
    }

    updateCropFramePosition();
}

function onDragTouch(e) {
    if (!cropState.dragMode || e.touches.length !== 1) return;
    e.preventDefault();

    const deltaX = e.touches[0].clientX - cropState.dragStartX;
    const deltaY = e.touches[0].clientY - cropState.dragStartY;

    if (cropState.dragMode === 'move') {
        let newX = cropState.startFrameX + deltaX;
        let newY = cropState.startFrameY + deltaY;

        newX = Math.max(cropState.imgLeft, Math.min(cropState.imgLeft + cropState.imgWidth - cropState.frameSize, newX));
        newY = Math.max(cropState.imgTop, Math.min(cropState.imgTop + cropState.imgHeight - cropState.frameSize, newY));

        cropState.frameX = newX;
        cropState.frameY = newY;
    } else if (cropState.dragMode === 'resize') {
        const minSize = 60;
        const maxSize = Math.min(cropState.imgWidth, cropState.imgHeight);
        const handle = cropState.activeHandle;

        let newFrameX = cropState.startFrameX;
        let newFrameY = cropState.startFrameY;
        let newFrameSize = cropState.startFrameSize;

        if (handle === 'se') {
            newFrameSize = cropState.startFrameSize + Math.max(deltaX, deltaY);
        } else if (handle === 'nw') {
            const sizeDelta = Math.max(deltaX, deltaY);
            newFrameSize = cropState.startFrameSize - sizeDelta;
            newFrameX = cropState.startFrameX + (cropState.startFrameSize - newFrameSize);
            newFrameY = cropState.startFrameY + (cropState.startFrameSize - newFrameSize);
        } else if (handle === 'ne') {
            newFrameSize = cropState.startFrameSize + Math.max(deltaX, -deltaY);
            newFrameY = cropState.startFrameY - (newFrameSize - cropState.startFrameSize);
        } else if (handle === 'sw') {
            newFrameSize = cropState.startFrameSize + Math.max(-deltaX, deltaY);
            newFrameX = cropState.startFrameX + (cropState.startFrameSize - newFrameSize);
        } else if (handle === 'n') {
            newFrameSize = cropState.startFrameSize - deltaY;
            newFrameY = cropState.startFrameY + deltaY;
        } else if (handle === 's') {
            newFrameSize = cropState.startFrameSize + deltaY;
        } else if (handle === 'w') {
            newFrameSize = cropState.startFrameSize - deltaX;
            newFrameX = cropState.startFrameX + deltaX;
        } else if (handle === 'e') {
            newFrameSize = cropState.startFrameSize + deltaX;
        }

        newFrameSize = Math.max(minSize, Math.min(maxSize, newFrameSize));

        if (handle === 'nw' || handle === 'n' || handle === 'w') {
            const sizeDiff = cropState.startFrameSize - newFrameSize;
            if (handle === 'nw' || handle === 'w') {
                newFrameX = cropState.startFrameX + sizeDiff;
            }
            if (handle === 'nw' || handle === 'n') {
                newFrameY = cropState.startFrameY + sizeDiff;
            }
        }

        newFrameX = Math.max(cropState.imgLeft, newFrameX);
        newFrameY = Math.max(cropState.imgTop, newFrameY);

        if (newFrameX + newFrameSize > cropState.imgLeft + cropState.imgWidth) {
            newFrameSize = cropState.imgLeft + cropState.imgWidth - newFrameX;
        }
        if (newFrameY + newFrameSize > cropState.imgTop + cropState.imgHeight) {
            newFrameSize = cropState.imgTop + cropState.imgHeight - newFrameY;
        }

        cropState.frameX = newFrameX;
        cropState.frameY = newFrameY;
        cropState.frameSize = Math.max(minSize, newFrameSize);
    }

    updateCropFramePosition();

    cropState.dragStartX = e.touches[0].clientX;
    cropState.dragStartY = e.touches[0].clientY;
}

function endDrag() {
    cropState.dragMode = null;
    cropState.activeHandle = null;
}

function closeCropper() {
    document.getElementById('cropperModal').classList.add('hidden');
    document.getElementById('avatarInput').value = '';
    
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('mouseup', endDrag);
    document.removeEventListener('touchmove', onDragTouch);
    document.removeEventListener('touchend', endDrag);
    
    document.querySelectorAll('.resize-handle').forEach(handle => {
        handle.removeEventListener('mousedown', startResize);
        handle.removeEventListener('touchstart', startResizeTouch);
    });
    
    if (cropState.cropCircle) {
        cropState.cropCircle.removeEventListener('mousedown', startMove);
        cropState.cropCircle.removeEventListener('touchstart', startMoveTouch);
    }
}

function saveCropDirect() {
    const relFrameX = cropState.frameX - cropState.imgLeft;
    const relFrameY = cropState.frameY - cropState.imgTop;
    
    const offsetX = (relFrameX / cropState.imgWidth) * 100;
    const offsetY = (relFrameY / cropState.imgHeight) * 100;
    const sizePercent = (cropState.frameSize / cropState.imgWidth) * 100;
    
    document.getElementById(cropState.cropXId).value = offsetX.toFixed(4);
    document.getElementById(cropState.cropYId).value = offsetY.toFixed(4);
    document.getElementById(cropState.cropSizeId).value = sizePercent.toFixed(4);
    
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const size = 200;
    canvas.width = size;
    canvas.height = size;
    
    const img = cropState.img;
    const scale = img.naturalWidth / cropState.imgWidth;
    
    const sx = relFrameX * scale;
    const sy = relFrameY * scale;
    const sSize = cropState.frameSize * scale;
    
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    ctx.closePath();
    ctx.clip();
    
    ctx.drawImage(img, sx, sy, sSize, sSize, 0, 0, size, size);
    
    const croppedDataUrl = canvas.toDataURL('image/png');
    
    const preview = document.getElementById(cropState.previewId);
    preview.innerHTML = '<img src="' + croppedDataUrl + '" class="w-24 h-24 rounded-full object-cover">';
    
    document.getElementById('cropperModal').classList.add('hidden');
}

function saveCropAjax() {
    const relFrameX = cropState.frameX - cropState.imgLeft;
    const relFrameY = cropState.frameY - cropState.imgTop;
    
    const offsetX = (relFrameX / cropState.imgWidth) * 100;
    const offsetY = (relFrameY / cropState.imgHeight) * 100;
    const sizePercent = (cropState.frameSize / cropState.imgWidth) * 100;
    
    const fileInput = document.getElementById('avatarInput');
    if (!fileInput.files[0]) {
        document.getElementById('cropperModal').classList.add('hidden');
        return;
    }
    
    const formData = new FormData();
    formData.append('avatar', fileInput.files[0]);
    formData.append('crop_x', offsetX.toFixed(4));
    formData.append('crop_y', offsetY.toFixed(4));
    formData.append('crop_size', sizePercent.toFixed(4));
    
    fetch(cropState.uploadUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': cropState.csrfToken
        }
    })
    .then(response => {
        window.location.reload();
    })
    .catch(error => {
        window.location.reload();
    });
}