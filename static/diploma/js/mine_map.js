document.addEventListener('DOMContentLoaded', function() {
    console.log('Debug: mine_map.js loaded');

    // Перевірка бібліотек
    if (typeof fabric === 'undefined') {
        console.error('Debug: Fabric.js not loaded - check CDN or adblocker');
        alert('Помилка: Fabric.js не завантажено. Вимкніть adblocker або перевірте мережу');
        return;
    }
    if (typeof THREE === 'undefined') {
        console.error('Debug: Three.js not loaded');
        alert('Помилка: Three.js не завантажено');
        return;
    }
    console.log('Debug: Fabric.js and Three.js loaded successfully');

    // Ініціалізація canvas
    const mapContainer = document.querySelector('.map-container');
    if (!mapContainer) {
        console.error('Debug: .map-container not found');
        return;
    }
    const canvas = new fabric.Canvas('map-canvas', {
        width: mapContainer.offsetWidth,
        height: mapContainer.offsetHeight,
        backgroundColor: '#333'
    });
    let is3D = false;
    let isEditMode = false;
    let scene, camera, renderer, cube;
    let selectedObject = null;

    // Ініціалізація 3D
    function init3D() {
        console.log('Debug: Initializing 3D view');
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(75, mapContainer.offsetWidth / mapContainer.offsetHeight, 0.1, 1000);
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(mapContainer.offsetWidth, mapContainer.offsetHeight);
        document.getElementById('map-3d').appendChild(renderer.domElement);

        const geometry = new THREE.BoxGeometry(1, 1, 1);
        const material = new THREE.MeshBasicMaterial({ color: 0x4dabf7 });
        cube = new THREE.Mesh(geometry, material);
        scene.add(cube);
        camera.position.z = 5;

        animate3D();
    }

    function animate3D() {
        if (is3D) {
            requestAnimationFrame(animate3D);
            cube.rotation.x += 0.01;
            cube.rotation.y += 0.01;
            renderer.render(scene, camera);
        }
    }

    // Завантаження даних
    let mapData = initialMapData || { tunnels: [], wifi: [], equipment: [] };
    console.log('Debug: Initial mapData', mapData);
    function loadMapData() {
        canvas.clear();
        canvas.setBackgroundColor('#333', canvas.renderAll.bind(canvas));
        try {
            mapData.tunnels.forEach(tunnel => {
                console.log('Debug: Loading tunnel', tunnel);
                canvas.add(new fabric.Rect(tunnel));
            });
            mapData.wifi.forEach(point => {
                console.log('Debug: Loading wifi point', point);
                canvas.add(new fabric.Circle(point));
            });
            mapData.equipment.forEach(eq => {
                console.log('Debug: Loading equipment', eq);
                canvas.add(eq.type === 'lift' ? new fabric.Circle(eq) : new fabric.Rect(eq));
            });
            updateListsAndStats();
        } catch (error) {
            console.error('Debug: Error loading mapData', error);
        }
    }
    loadMapData();

    // Оновлення списків і статистики
    function updateListsAndStats() {
        console.log('Debug: Updating lists and stats');
        const lists = {
            tunnels: document.getElementById('tunnels-list'),
            wifi: document.getElementById('wifi-list'),
            combine: document.getElementById('combine-list'),
            lift: document.getElementById('lift-list'),
            conveyor: document.getElementById('conveyor-list'),
            drill: document.getElementById('drill-list')
        };
        Object.values(lists).forEach(list => list.innerHTML = '');
        mapData.tunnels.forEach((t, i) => addListItem(lists.tunnels, `Тунель ${i + 1}`, t));
        mapData.wifi.forEach((w, i) => addListItem(lists.wifi, `Wi-Fi ${i + 1}`, w));
        mapData.equipment.forEach((e, i) => {
            const list = e.type === 'combine' ? lists.combine :
                        e.type === 'lift' ? lists.lift :
                        e.type === 'conveyor' ? lists.conveyor : lists.drill;
            addListItem(list, `${e.type.charAt(0).toUpperCase() + e.type.slice(1)} ${i + 1}`, e);
        });
        document.getElementById('stats-tunnels').textContent = mapData.tunnels.length;
        document.getElementById('stats-wifi').textContent = mapData.wifi.length;
        document.getElementById('stats-equipment').textContent = mapData.equipment.length;
    }

    function addListItem(list, name, obj) {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>${name}</span>
            <div>
                <button class="edit-btn btn"><i class="fas fa-edit"></i></button>
                <button class="delete-btn btn"><i class="fas fa-trash"></i></button>
                <button class="duplicate-btn btn"><i class="fas fa-copy"></i></button>
            </div>
        `;
        li.querySelector('.edit-btn').addEventListener('click', () => selectObject(obj));
        li.querySelector('.delete-btn').addEventListener('click', () => deleteObject(obj));
        li.querySelector('.duplicate-btn').addEventListener('click', () => duplicateObject(obj));
        list.appendChild(li);
    }

    // Switch редагування
    const editSwitch = document.getElementById('edit-mode-switch');
    if (editSwitch) {
        editSwitch.addEventListener('change', (e) => {
            isEditMode = e.target.checked;
            console.log('Debug: Edit mode changed to', isEditMode);
            const addMenu = document.querySelector('.add-menu');
            const saveBtn = document.getElementById('save-map');
            if (addMenu) addMenu.style.display = isEditMode ? 'block' : 'none';
            if (saveBtn) saveBtn.style.display = isEditMode ? 'block' : 'none';
            canvas.selection = isEditMode;
            canvas.forEachObject(obj => obj.selectable = isEditMode);
            canvas.renderAll();
        });
    } else {
        console.error('Debug: edit-mode-switch not found');
    }

    // Вибір об'єкта
    function selectObject(obj) {
        console.log('Debug: Selecting object', obj);
        canvas.setActiveObject(obj);
        selectedObject = obj;
        updatePropertiesPanel();
    }

    function updatePropertiesPanel() {
        console.log('Debug: Updating properties panel');
        const typeEl = document.getElementById('prop-type');
        const leftEl = document.getElementById('prop-left');
        const topEl = document.getElementById('prop-top');
        const widthEl = document.getElementById('prop-width');
        const heightEl = document.getElementById('prop-height');
        const radiusEl = document.getElementById('prop-radius');
        if (!selectedObject) {
            typeEl.textContent = 'Невідомий';
            leftEl.value = '';
            topEl.value = '';
            widthEl.value = '';
            heightEl.value = '';
            radiusEl.value = '';
            return;
        }
        typeEl.textContent = selectedObject.type || 'Невідомий';
        leftEl.value = selectedObject.left || 0;
        topEl.value = selectedObject.top || 0;
        widthEl.value = selectedObject.width || '';
        heightEl.value = selectedObject.height || '';
        radiusEl.value = selectedObject.radius || '';
        [leftEl, topEl, widthEl, heightEl, radiusEl].forEach(el => el.disabled = !isEditMode);
    }

    canvas.on('selection:created', (e) => {
        selectedObject = e.target;
        updatePropertiesPanel();
    });
    canvas.on('selection:updated', (e) => {
        selectedObject = e.target;
        updatePropertiesPanel();
    });
    canvas.on('selection:cleared', () => {
        selectedObject = null;
        updatePropertiesPanel();
    });

    // Додавання об'єктів
    function addObject(type, props) {
        console.log(`Debug: Adding ${type}`);
        const obj = type === 'circle' ? new fabric.Circle(props) : new fabric.Rect(props);
        canvas.add(obj);
        mapData[type === 'circle' ? 'wifi' : type === 'tunnel' ? 'tunnels' : 'equipment'].push(props);
        updateListsAndStats();
        canvas.renderAll();
    }

    document.getElementById('add-tunnel').addEventListener('click', () => addObject('tunnel', {
        left: 50, top: 50, width: 100, height: 20, fill: 'gray', selectable: true
    }));
    document.getElementById('add-wifi').addEventListener('click', () => addObject('circle', {
        left: 100, top: 100, radius: 10, fill: 'blue', selectable: true
    }));
    document.getElementById('add-combine').addEventListener('click', () => addObject('equipment', {
        left: 150, top: 150, width: 50, height: 30, fill: 'red', selectable: true, type: 'combine'
    }));
    document.getElementById('add-lift').addEventListener('click', () => addObject('circle', {
        left: 200, top: 200, radius: 15, fill: 'green', selectable: true, type: 'lift'
    }));
    document.getElementById('add-conveyor').addEventListener('click', () => addObject('equipment', {
        left: 250, top: 250, width: 80, height: 15, fill: 'purple', selectable: true, type: 'conveyor'
    }));
    document.getElementById('add-drill').addEventListener('click', () => addObject('equipment', {
        left: 300, top: 300, width: 40, height: 40, fill: 'orange', selectable: true, type: 'drill'
    }));

    // Застосування властивостей
    document.getElementById('apply-properties').addEventListener('click', () => {
        if (!selectedObject || !isEditMode) return;
        console.log('Debug: Applying properties');
        selectedObject.set({
            left: parseFloat(document.getElementById('prop-left').value) || selectedObject.left,
            top: parseFloat(document.getElementById('prop-top').value) || selectedObject.top,
            width: parseFloat(document.getElementById('prop-width').value) || selectedObject.width,
            height: parseFloat(document.getElementById('prop-height').value) || selectedObject.height,
            radius: parseFloat(document.getElementById('prop-radius').value) || selectedObject.radius
        });
        canvas.renderAll();
        updateMapData();
        updateListsAndStats();
    });

    // Видалення об'єкта
    function deleteObject(obj) {
        console.log('Debug: Deleting object', obj);
        canvas.remove(obj);
        ['tunnels', 'wifi', 'equipment'].forEach(key => {
            mapData[key] = mapData[key].filter(item => item !== obj);
        });
        updateListsAndStats();
        canvas.renderAll();
    }

    document.getElementById('delete-object').addEventListener('click', () => {
        if (selectedObject) deleteObject(selectedObject);
    });

    // Дублювання об'єкта
    function duplicateObject(obj) {
        console.log('Debug: Duplicating object', obj);
        const newObj = fabric.util.object.clone(obj);
        newObj.set({ left: obj.left + 10, top: obj.top + 10 });
        canvas.add(newObj);
        mapData[obj.type === 'circle' ? 'wifi' : obj.type === 'tunnel' ? 'tunnels' : 'equipment'].push(newObj);
        updateListsAndStats();
        canvas.renderAll();
    }

    // Збереження карти
    document.getElementById('save-map').addEventListener('click', () => {
        console.log('Debug: Saving mapData', mapData);
        document.getElementById('loading-message').style.display = 'block';
        fetch('/diploma/mine_map/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: 'map_data=' + encodeURIComponent(JSON.stringify(mapData))
        })
        .then(response => {
            console.log('Debug: Save response status', response.status);
            return response.json();
        })
        .then(data => {
            document.getElementById('loading-message').style.display = 'none';
            if (data.status === 'success') {
                document.querySelector('.last-edited').textContent = `Останній редагував: ${data.last_edited_by}`;
                document.getElementById('success-message').style.display = 'block';
                setTimeout(() => document.getElementById('success-message').style.display = 'none', 2000);
                console.log('Debug: Map saved successfully', data);
            } else {
                console.error('Debug: Save failed', data);
            }
        })
        .catch(error => {
            document.getElementById('loading-message').style.display = 'none';
            console.error('Debug: Save fetch error', error);
        });
    });

    // Експорт JSON
    document.getElementById('export-json').addEventListener('click', () => {
        console.log('Debug: Exporting JSON');
        const json = JSON.stringify(mapData, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'mine_map.json';
        a.click();
        URL.revokeObjectURL(url);
    });

    // Завантаження JSON
    document.getElementById('download-map').addEventListener('click', () => {
        console.log('Debug: Downloading map');
        document.getElementById('loading-message').style.display = 'block';
        fetch('/diploma/download_map/')
        .then(response => {
            console.log('Debug: Download response status', response.status);
            return response.blob();
        })
        .then(blob => {
            document.getElementById('loading-message').style.display = 'none';
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mine_map.json';
            a.click();
            URL.revokeObjectURL(url);
            document.getElementById('success-message').style.display = 'block';
            setTimeout(() => document.getElementById('success-message').style.display = 'none', 2000);
        })
        .catch(error => {
            document.getElementById('loading-message').style.display = 'none';
            console.error('Debug: Download fetch error', error);
        });
    });

    // Допомога
    document.getElementById('help-btn').addEventListener('click', () => {
        console.log('Debug: Help button clicked');
        alert('Інструкція:\n1. Увімкніть режим редагування.\n2. Додавайте тунелі, Wi-Fi точки, техніку через меню.\n3. Редагуйте властивості в панелі.\n4. Збережіть або експортуйте карту.');
    });

    // Перемикання 2D/3D
    document.getElementById('toggle-2d-3d').addEventListener('click', () => {
        is3D = !is3D;
        console.log('Debug: Toggle 2D/3D to', is3D ? '3D' : '2D');
        document.getElementById('map-canvas').style.display = is3D ? 'none' : 'block';
        document.getElementById('map-3d').style.display = is3D ? 'block' : 'none';
        if (is3D && !scene) init3D();
    });

    // Resize
    window.addEventListener('resize', () => {
        console.log('Debug: Window resized');
        canvas.setDimensions({
            width: mapContainer.offsetWidth,
            height: mapContainer.offsetHeight
        });
        if (is3D && renderer) {
            renderer.setSize(mapContainer.offsetWidth, mapContainer.offsetHeight);
            camera.aspect = mapContainer.offsetWidth / mapContainer.offsetHeight;
            camera.updateProjectionMatrix();
        }
        canvas.renderAll();
    });

    function updateMapData() {
        console.log('Debug: Updating mapData');
        mapData.tunnels = canvas.getObjects().filter(o => o.type === 'rect' && !o.type.includes('equipment')).map(o => ({
            left: o.left, top: o.top, width: o.width, height: o.height, fill: o.fill
        }));
        mapData.wifi = canvas.getObjects().filter(o => o.type === 'circle' && !o.type.includes('equipment')).map(o => ({
            left: o.left, top: o.top, radius: o.radius, fill: o.fill
        }));
        mapData.equipment = canvas.getObjects().filter(o => o.type.includes('equipment')).map(o => ({
            left: o.left, top: o.top, width: o.width, height: o.height, radius: o.radius, fill: o.fill, type: o.type
        }));
    }
});