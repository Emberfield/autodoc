// Autodoc Configuration UI

document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    setupEventListeners();
});

function setupEventListeners() {
    // Form submission
    document.getElementById('config-form').addEventListener('submit', handleSubmit);

    // Reset button
    document.getElementById('reset-btn').addEventListener('click', resetToDefaults);

    // Add context pack button
    document.getElementById('add-pack-btn').addEventListener('click', addContextPack);
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error('Failed to load configuration');
        }
        const config = await response.json();
        populateForm(config);
    } catch (error) {
        showMessage('Error loading configuration: ' + error.message, 'error');
    }
}

function populateForm(config) {
    // LLM settings
    if (config.llm) {
        setValue('llm-provider', config.llm.provider);
        setValue('llm-model', config.llm.model);
        setValue('llm-temperature', config.llm.temperature);
        setValue('llm-max-tokens', config.llm.max_tokens);
        setValue('llm-base-url', config.llm.base_url);
    }

    // Enrichment settings
    if (config.enrichment) {
        setChecked('enrichment-enabled', config.enrichment.enabled);
        setValue('enrichment-batch-size', config.enrichment.batch_size);
        setChecked('enrichment-cache', config.enrichment.cache_enrichments);
        setChecked('enrichment-examples', config.enrichment.include_examples);
        setChecked('enrichment-complexity', config.enrichment.analyze_complexity);
        setChecked('enrichment-patterns', config.enrichment.detect_patterns);
        if (config.enrichment.languages) {
            setValue('enrichment-languages', config.enrichment.languages.join(', '));
        }
    }

    // Embeddings settings
    if (config.embeddings) {
        setValue('embeddings-provider', config.embeddings.provider);
        setValue('embeddings-model', config.embeddings.model);
        setValue('embeddings-chromadb-model', config.embeddings.chromadb_model);
        setValue('embeddings-dimensions', config.embeddings.dimensions);
        setValue('embeddings-batch-size', config.embeddings.batch_size);
        setValue('embeddings-persist-dir', config.embeddings.persist_directory);
    }

    // Graph settings
    if (config.graph) {
        setValue('graph-uri', config.graph.neo4j_uri);
        setValue('graph-username', config.graph.neo4j_username);
        setChecked('graph-enrich', config.graph.enrich_nodes);
    }

    // Analysis settings
    if (config.analysis) {
        if (config.analysis.ignore_patterns) {
            setValue('analysis-ignore', config.analysis.ignore_patterns.join('\n'));
        }
        setValue('analysis-max-size', config.analysis.max_file_size);
        setChecked('analysis-follow-imports', config.analysis.follow_imports);
        setChecked('analysis-dependencies', config.analysis.analyze_dependencies);
    }

    // Output settings
    if (config.output) {
        setValue('output-format', config.output.format);
        setValue('output-max-desc', config.output.max_description_length);
        setChecked('output-snippets', config.output.include_code_snippets);
        setChecked('output-group', config.output.group_by_feature);
    }

    // Database settings
    if (config.database) {
        if (config.database.migration_paths) {
            setValue('db-migrations', config.database.migration_paths.join('\n'));
        }
        if (config.database.model_paths) {
            setValue('db-models', config.database.model_paths.join('\n'));
        }
        setChecked('db-analyze', config.database.analyze_schema);
    }

    // Context packs - clear existing and repopulate
    const container = document.getElementById('context-packs-container');
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    if (config.context_packs && config.context_packs.length > 0) {
        config.context_packs.forEach(pack => addContextPack(pack));
    }
}

function setValue(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
        el.value = value;
    }
}

function setChecked(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.checked = !!value;
    }
}

function getValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : null;
}

function getChecked(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
}

function getConfig() {
    const config = {
        llm: {
            provider: getValue('llm-provider'),
            model: getValue('llm-model'),
            temperature: parseFloat(getValue('llm-temperature')) || 0.3,
            max_tokens: parseInt(getValue('llm-max-tokens')) || 500
        },
        enrichment: {
            enabled: getChecked('enrichment-enabled'),
            batch_size: parseInt(getValue('enrichment-batch-size')) || 10,
            cache_enrichments: getChecked('enrichment-cache'),
            include_examples: getChecked('enrichment-examples'),
            analyze_complexity: getChecked('enrichment-complexity'),
            detect_patterns: getChecked('enrichment-patterns'),
            languages: parseList(getValue('enrichment-languages'))
        },
        embeddings: {
            provider: getValue('embeddings-provider'),
            model: getValue('embeddings-model'),
            chromadb_model: getValue('embeddings-chromadb-model'),
            dimensions: parseInt(getValue('embeddings-dimensions')) || 1536,
            batch_size: parseInt(getValue('embeddings-batch-size')) || 100,
            persist_directory: getValue('embeddings-persist-dir')
        },
        graph: {
            neo4j_uri: getValue('graph-uri'),
            neo4j_username: getValue('graph-username'),
            enrich_nodes: getChecked('graph-enrich')
        },
        analysis: {
            ignore_patterns: parseLines(getValue('analysis-ignore')),
            max_file_size: parseInt(getValue('analysis-max-size')) || 1048576,
            follow_imports: getChecked('analysis-follow-imports'),
            analyze_dependencies: getChecked('analysis-dependencies')
        },
        output: {
            format: getValue('output-format'),
            max_description_length: parseInt(getValue('output-max-desc')) || 500,
            include_code_snippets: getChecked('output-snippets'),
            group_by_feature: getChecked('output-group')
        },
        database: {
            migration_paths: parseLines(getValue('db-migrations')),
            model_paths: parseLines(getValue('db-models')),
            analyze_schema: getChecked('db-analyze')
        },
        context_packs: getContextPacks()
    };

    // Add optional base_url if set
    const baseUrl = getValue('llm-base-url');
    if (baseUrl) {
        config.llm.base_url = baseUrl;
    }

    return config;
}

function parseList(value) {
    if (!value) return [];
    return value.split(',').map(s => s.trim()).filter(s => s);
}

function parseLines(value) {
    if (!value) return [];
    return value.split('\n').map(s => s.trim()).filter(s => s);
}

function getContextPacks() {
    const packs = [];
    const container = document.getElementById('context-packs-container');
    const packElements = container.querySelectorAll('.context-pack');

    packElements.forEach(packEl => {
        const name = packEl.querySelector('.pack-name').value.trim();
        const displayName = packEl.querySelector('.pack-display-name').value.trim();
        const description = packEl.querySelector('.pack-description').value.trim();

        if (name && displayName && description) {
            const pack = {
                name: name,
                display_name: displayName,
                description: description,
                files: parseLines(packEl.querySelector('.pack-files').value),
                tables: parseList(packEl.querySelector('.pack-tables').value),
                dependencies: parseList(packEl.querySelector('.pack-dependencies').value),
                tags: parseList(packEl.querySelector('.pack-tags').value)
            };

            const securityLevel = packEl.querySelector('.pack-security').value;
            if (securityLevel) {
                pack.security_level = securityLevel;
            }

            packs.push(pack);
        }
    });

    return packs;
}

function addContextPack(packData = null) {
    const template = document.getElementById('pack-template');
    const clone = template.content.cloneNode(true);
    const packEl = clone.querySelector('.context-pack');

    // Set up remove button
    packEl.querySelector('.btn-remove').addEventListener('click', () => {
        packEl.remove();
    });

    // Update title when name changes
    const nameInput = packEl.querySelector('.pack-name');
    const titleEl = packEl.querySelector('.pack-title');
    nameInput.addEventListener('input', () => {
        titleEl.textContent = nameInput.value || 'New Pack';
    });

    // Populate if data provided
    if (packData) {
        packEl.querySelector('.pack-name').value = packData.name || '';
        packEl.querySelector('.pack-display-name').value = packData.display_name || '';
        packEl.querySelector('.pack-description').value = packData.description || '';
        packEl.querySelector('.pack-files').value = (packData.files || []).join('\n');
        packEl.querySelector('.pack-tables').value = (packData.tables || []).join(', ');
        packEl.querySelector('.pack-dependencies').value = (packData.dependencies || []).join(', ');
        packEl.querySelector('.pack-security').value = packData.security_level || '';
        packEl.querySelector('.pack-tags').value = (packData.tags || []).join(', ');
        titleEl.textContent = packData.name || 'New Pack';
    }

    document.getElementById('context-packs-container').appendChild(packEl);
}

async function handleSubmit(event) {
    event.preventDefault();

    const config = getConfig();

    try {
        const response = await fetch('/api/config', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Failed to save configuration');
        }

        showMessage('Configuration saved successfully!', 'success');
    } catch (error) {
        showMessage('Error saving configuration: ' + error.message, 'error');
    }
}

async function resetToDefaults() {
    if (!confirm('Are you sure you want to reset to default configuration?')) {
        return;
    }

    // Create a default config
    const defaultConfig = {
        llm: {
            provider: 'openai',
            model: 'gpt-4o-mini',
            temperature: 0.3,
            max_tokens: 500
        },
        enrichment: {
            enabled: true,
            batch_size: 10,
            cache_enrichments: true,
            include_examples: true,
            analyze_complexity: true,
            detect_patterns: true,
            languages: ['python', 'typescript']
        },
        embeddings: {
            provider: 'openai',
            model: 'text-embedding-3-small',
            chromadb_model: 'all-MiniLM-L6-v2',
            dimensions: 1536,
            batch_size: 100,
            persist_directory: '.autodoc_chromadb'
        },
        graph: {
            neo4j_uri: 'bolt://localhost:7687',
            neo4j_username: 'neo4j',
            enrich_nodes: true
        },
        analysis: {
            ignore_patterns: ['__pycache__', '*.pyc', '.git', 'node_modules'],
            max_file_size: 1048576,
            follow_imports: true,
            analyze_dependencies: true
        },
        output: {
            format: 'markdown',
            max_description_length: 500,
            include_code_snippets: true,
            group_by_feature: true
        },
        database: {
            migration_paths: ['init/postgres/*.sql', 'alembic/versions/*.py', 'migrations/*.sql'],
            model_paths: ['api/models/*.py', 'src/models/*.py', '**/models.py'],
            analyze_schema: false
        },
        context_packs: []
    };

    populateForm(defaultConfig);
    showMessage('Form reset to defaults. Click Save to apply changes.', 'success');
}

function showMessage(text, type) {
    const messageEl = document.getElementById('message');
    messageEl.textContent = text;
    messageEl.className = 'message ' + type;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageEl.classList.add('hidden');
    }, 5000);
}
