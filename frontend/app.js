// Configuration
const API_BASE = 'http://localhost:8000';

// State
let currentUser = null;
let profileData = {};
let conversationStarted = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadExistingUsers();
    
    // Check if user is already logged in
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        showMainApp();
    }
});

// ============================================================================
// User Session Management
// ============================================================================

async function startSession() {
    const email = document.getElementById('user-email').value.trim();
    const name = document.getElementById('user-name').value.trim();
    
    if (!email || !name) {
        alert('Please enter both email and name');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/profile/start?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        currentUser = {
            id: data.user_id,
            email: email,
            name: name
        };
        
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        // Add first agent message
        addMessage('agent', data.message);
        conversationStarted = true;
        
        showMainApp();
    } catch (error) {
        console.error('Error starting session:', error);
        alert('Failed to start session. Please try again.');
    }
}

function selectExistingUser(user) {
    currentUser = {
        id: user.id,
        email: user.email,
        name: user.name
    };
    
    localStorage.setItem('currentUser', JSON.stringify(currentUser));
    showMainApp();
}

function logout() {
    currentUser = null;
    localStorage.removeItem('currentUser');
    document.getElementById('user-selection').style.display = 'block';
    document.getElementById('main-app').style.display = 'none';
    
    // Clear chat
    document.getElementById('profile-messages').innerHTML = '';
    conversationStarted = false;
}

function showMainApp() {
    document.getElementById('user-selection').style.display = 'none';
    document.getElementById('main-app').style.display = 'block';
    document.getElementById('current-user').textContent = `👤 ${currentUser.name}`;

    loadConnections();
    loadAllUsers();

    // Initialize profile chat if not already started
    if (!conversationStarted) {
        initializeProfileChat();
    }
}

// Initialize profile building conversation
async function initializeProfileChat() {
    if (!currentUser || !currentUser.id) return;

    try {
        // Check if user already has a profile
        const profileResponse = await fetch(`${API_BASE}/api/profile/${currentUser.id}`);
        const profileData = await profileResponse.json();

        // If user has a complete profile, show a welcome back message
        if (profileData && profileData.profile && profileData.profile.title) {
            addMessage('agent', `Welcome back, ${currentUser.name}! Your profile is already set up. Feel free to update it by chatting with me, or head to the Search tab to find professionals in your network.`);
            conversationStarted = true;
            return;
        }

        // Start profile building for users without a complete profile
        const response = await fetch(`${API_BASE}/api/profile/start?email=${encodeURIComponent(currentUser.email)}&name=${encodeURIComponent(currentUser.name)}`, {
            method: 'POST'
        });

        const data = await response.json();

        // Update user ID in case it changed
        currentUser.id = data.user_id;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));

        // Add first agent message
        addMessage('agent', data.message);
        conversationStarted = true;

    } catch (error) {
        console.error('Error initializing profile chat:', error);
        addMessage('agent', `Hi ${currentUser.name}! I'm here to help you build your professional profile. Let's start - what is your current job title or professional role?`);
        conversationStarted = true;
    }
}

// ============================================================================
// Tab Management
// ============================================================================

function showTab(tabName) {
    // Update tabs
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Refresh data when switching tabs
    if (tabName === 'connections') {
        loadConnections();
    }
}

// ============================================================================
// Profile Building
// ============================================================================

async function sendProfileMessage() {
    if (!currentUser || !currentUser.id) {
        addMessage('agent', 'Session error. Please log out and log back in.');
        return;
    }

    const input = document.getElementById('profile-input');
    const message = input.value.trim();

    if (!message) return;

    // Add user message to chat
    addMessage('user', message);
    input.value = '';

    // Show typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message agent typing';
    typingDiv.innerHTML = '<strong>🤖 Agent</strong><div>Thinking...</div>';
    document.getElementById('profile-messages').appendChild(typingDiv);

    try {
        const response = await fetch(`${API_BASE}/api/profile/chat?user_id=${currentUser.id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_message: message })
        });

        // Remove typing indicator
        typingDiv.remove();

        const data = await response.json();

        // Add agent response
        addMessage('agent', data.message);

        // Update profile data
        if (data.profile_data) {
            profileData = data.profile_data;
            updateProfileProgress(data.profile_data, data.missing_fields || []);
        }

        // Show profile preview if complete
        if (data.is_complete) {
            showProfilePreview();
        }
    } catch (error) {
        typingDiv.remove();
        console.error('Error sending message:', error);
        addMessage('agent', 'Sorry, I encountered an error. Please try again.');
    }
}

function updateProfileProgress(profile, missingFields) {
    const progressDiv = document.getElementById('profile-progress');
    if (!progressDiv) return;

    const fields = [
        { key: 'title', label: 'Title' },
        { key: 'skills', label: 'Skills' },
        { key: 'experience_years', label: 'Experience' },
        { key: 'availability', label: 'Availability' },
        { key: 'location', label: 'Location' },
        { key: 'bio', label: 'Bio' }
    ];

    const completedCount = fields.filter(f => {
        const val = profile[f.key];
        return val !== null && val !== undefined && (Array.isArray(val) ? val.length > 0 : true);
    }).length;

    const percentage = Math.round((completedCount / fields.length) * 100);

    progressDiv.innerHTML = `
        <div class="progress-header">Profile Completion: ${percentage}%</div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${percentage}%"></div>
        </div>
        <div class="progress-fields">
            ${fields.map(f => {
                const val = profile[f.key];
                const isComplete = val !== null && val !== undefined && (Array.isArray(val) ? val.length > 0 : true);
                return `<span class="field-status ${isComplete ? 'complete' : 'pending'}">${f.label}</span>`;
            }).join('')}
        </div>
    `;

    progressDiv.style.display = 'block';
}

function addMessage(type, text) {
    const messagesDiv = document.getElementById('profile-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const label = document.createElement('strong');
    label.textContent = type === 'agent' ? '🤖 Agent' : '👤 You';
    
    const content = document.createElement('div');
    content.textContent = text;
    
    messageDiv.appendChild(label);
    messageDiv.appendChild(content);
    messagesDiv.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function showProfilePreview() {
    const previewDiv = document.getElementById('profile-data');
    const contentDiv = document.getElementById('profile-preview-content');

    const locationStr = profileData.location
        ? `${profileData.location.city || ''}${profileData.location.city && profileData.location.country ? ', ' : ''}${profileData.location.country || ''}`
        : 'Not provided';

    contentDiv.innerHTML = `
        <div class="profile-field">
            <label>Title:</label>
            <div>${profileData.title || 'Not provided'}</div>
        </div>
        <div class="profile-field">
            <label>Skills:</label>
            <div class="skills-list">${(profileData.skills || []).map(s => `<span class="skill-tag">${s}</span>`).join('') || 'Not provided'}</div>
        </div>
        <div class="profile-field">
            <label>Experience:</label>
            <div>${profileData.experience_years ? `${profileData.experience_years} years` : 'Not provided'}</div>
        </div>
        <div class="profile-field">
            <label>Availability:</label>
            <div>${profileData.availability || 'Not provided'}</div>
        </div>
        <div class="profile-field">
            <label>Location:</label>
            <div>${locationStr}</div>
        </div>
        <div class="profile-field">
            <label>Bio:</label>
            <div>${profileData.bio || 'Not provided'}</div>
        </div>
    `;

    previewDiv.style.display = 'block';
}

async function saveProfile() {
    try {
        const response = await fetch(`${API_BASE}/api/profile/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                ...profileData
            })
        });
        
        const data = await response.json();
        
        alert('Profile saved successfully!');
        
        // Clear chat and hide preview
        document.getElementById('profile-messages').innerHTML = '';
        document.getElementById('profile-data').style.display = 'none';
        conversationStarted = false;
        
        // Switch to search tab
        showTab('search');
        document.querySelector('.tab:nth-child(2)').classList.add('active');
        document.querySelector('.tab:nth-child(1)').classList.remove('active');
        
    } catch (error) {
        console.error('Error saving profile:', error);
        alert('Failed to save profile. Please try again.');
    }
}

// ============================================================================
// Search Network
// ============================================================================

async function searchNetwork() {
    if (!currentUser || !currentUser.id) {
        alert('Session error. Please log out and log back in.');
        return;
    }

    const input = document.getElementById('search-input');
    const query = input.value.trim();

    if (!query) {
        alert('Please enter a search query');
        return;
    }
    
    // Show loading
    document.getElementById('search-loading').style.display = 'block';
    document.getElementById('search-results').innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                query_text: query
            })
        });
        
        const data = await response.json();
        
        // Hide loading
        document.getElementById('search-loading').style.display = 'none';
        
        // Display results
        displaySearchResults(data);
        
    } catch (error) {
        console.error('Error searching:', error);
        document.getElementById('search-loading').style.display = 'none';
        alert('Search failed. Please try again.');
    }
}

function displaySearchResults(data) {
    const resultsDiv = document.getElementById('search-results');
    
    if (!data.matches || data.matches.length === 0) {
        resultsDiv.innerHTML = `
            <div class="section">
                <p>No matches found. ${data.message || 'Try connecting with more people or adjusting your search.'}</p>
            </div>
        `;
        return;
    }
    
    resultsDiv.innerHTML = '';
    
    data.matches.forEach(match => {
        const card = document.createElement('div');
        card.className = 'result-card';
        
        const scorePercentage = (match.final_score * 100).toFixed(0);
        
        card.innerHTML = `
            <h3>${match.name}</h3>
            <div class="title">${match.title || 'Professional'}</div>
            
            <div class="score-bar">
                <div class="score-fill" style="width: ${scorePercentage}%"></div>
            </div>
            <div style="text-align: right; font-size: 0.9rem; color: var(--gray-700);">
                Match: ${scorePercentage}%
            </div>
            
            <div class="skills">
                ${match.matched_skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')}
            </div>
            
            <p style="margin-top: 15px; color: var(--gray-700); font-size: 0.9rem;">
                ${match.explanation}
            </p>
        `;
        
        resultsDiv.appendChild(card);
    });
}

// ============================================================================
// Connections
// ============================================================================

async function loadConnections() {
    if (!currentUser || !currentUser.id) return;

    try {
        const response = await fetch(`${API_BASE}/api/connections/${currentUser.id}`);
        const data = await response.json();
        
        const listDiv = document.getElementById('connections-list');
        
        if (!data.connections || data.connections.length === 0) {
            listDiv.innerHTML = '<p>No connections yet. Add some connections below!</p>';
            return;
        }
        
        listDiv.innerHTML = '';
        
        data.connections.forEach(conn => {
            const card = document.createElement('div');
            card.className = 'connection-card';
            
            card.innerHTML = `
                <h4>${conn.name}</h4>
                <div class="trust-score">Trust: ${(conn.trust_score * 100).toFixed(0)}%</div>
            `;
            
            listDiv.appendChild(card);
        });
        
    } catch (error) {
        console.error('Error loading connections:', error);
    }
}

async function loadAllUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/users`);
        const data = await response.json();
        
        const select = document.getElementById('connect-user-select');
        select.innerHTML = '<option value="">Select a user...</option>';
        
        data.users
            .filter(u => u.id !== currentUser.id)
            .forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.name} (${user.email})`;
                select.appendChild(option);
            });
        
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

async function addConnection() {
    if (!currentUser || !currentUser.id) {
        alert('Session error. Please log out and log back in.');
        return;
    }

    const select = document.getElementById('connect-user-select');
    const otherUserId = select.value;

    if (!otherUserId) {
        alert('Please select a user');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/connections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_a_id: currentUser.id,
                user_b_id: otherUserId
            })
        });
        
        const data = await response.json();
        
        alert('Connection created successfully!');
        loadConnections();
        
    } catch (error) {
        console.error('Error creating connection:', error);
        alert('Failed to create connection. Please try again.');
    }
}

// ============================================================================
// Load Existing Users
// ============================================================================

async function loadExistingUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/users`);
        const data = await response.json();
        
        const listDiv = document.getElementById('users-list');
        listDiv.innerHTML = '';
        
        if (!data.users || data.users.length === 0) {
            listDiv.innerHTML = '<p>No users yet. Be the first!</p>';
            return;
        }
        
        data.users.forEach(user => {
            const card = document.createElement('div');
            card.className = 'user-card';
            card.onclick = () => selectExistingUser(user);
            
            card.innerHTML = `
                <h4>${user.name}</h4>
                <p>${user.email}</p>
                ${user.title ? `<p><strong>${user.title}</strong></p>` : ''}
            `;
            
            listDiv.appendChild(card);
        });
        
    } catch (error) {
        console.error('Error loading users:', error);
    }
}
