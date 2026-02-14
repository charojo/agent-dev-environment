// ## @DOC
// ### Ade Unified Matrix
// Generates a unified test coverage matrix for backend and frontend.


const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const rootDir = path.join(__dirname, '..', '..');
const logsDir = path.join(rootDir, 'logs');
const outputFile = path.join(logsDir, 'test-coverage-matrix.txt');

console.log('Starting Unified Coverage Matrix Generation...');

// 1. Generate Backend Matrix
console.log('\n--- Generating Backend Matrix ---');
try {
    // Note: Script is now in agent_env/bin and has ADE_ prefix
    execSync('uv run python agent_env/bin/ADE_generate_backend_matrix.py', { cwd: rootDir, stdio: 'inherit' });
} catch (e) {
    console.error('Failed to generate backend matrix');
}

// 2. Generate Frontend Matrix
console.log('\n--- Generating Frontend Matrix ---');
try {
    // We assume the frontend script has been updated to output JSON to `logs/frontend_matrix.json`
    // or we just reuse the existing implementation but we need it to output JSON for merging.
    // For now, let's just make sure it runs.
    // If the frontend script outputs text directly, we can't easily merge properly without parsing.
    // Better to have frontend script output JSON.
    execSync('npm run test:coverage:matrix', { cwd: path.join(rootDir, 'src/web'), stdio: 'inherit' });
} catch (e) {
    console.error('Failed to generate frontend matrix');
}

// 3. Merge & Format
console.log('\n--- Merging Results ---');

let matrix = {}; // { testName: { modulePath: percentage } }

// Helper to merge
function mergeData(jsonPath) {
    if (fs.existsSync(jsonPath)) {
        try {
            const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
            for (const [testName, modules] of Object.entries(data)) {
                if (!matrix[testName]) matrix[testName] = {};

                // Backend data is { module: percent }
                // Frontend data (current matrix.js) is [ modulePath ] (list)
                // We need to update frontend script to output { module: percent } or handle list.

                if (Array.isArray(modules)) {
                    // Convert list to dict with "N/A" percentage or calculate it if possible
                    modules.forEach(mod => {
                        matrix[testName][mod] = 'Checked';
                    });
                } else {
                    // Assume object { module: percent }
                    for (const [mod, val] of Object.entries(modules)) {
                        matrix[testName][mod] = val;
                    }
                }
            }
        } catch (e) {
            console.error(`Error reading ${jsonPath}:`, e.message);
        }
    } else {
        console.warn(`File not found: ${jsonPath}`);
    }
}

mergeData(path.join(logsDir, 'backend_matrix.json'));
mergeData(path.join(logsDir, 'frontend_matrix.json'));

// Output Table
let output = 'Unified Test-to-Module Coverage Matrix\n';
output += '======================================\n\n';

const sortedTests = Object.keys(matrix).sort();
if (sortedTests.length === 0) {
    output += "No coverage data found.\n";
}

sortedTests.forEach(testName => {
    output += `Test: [ ${testName} ]\n`;
    const modules = matrix[testName];
    const sortedModules = Object.keys(modules).sort();

    sortedModules.forEach(mod => {
        const val = modules[mod];
        const valStr = (typeof val === 'number') ? `${val}%` : val;
        output += `  - ${mod.padEnd(60)} : ${valStr}\n`;
    });
    output += '\n';
});

fs.writeFileSync(outputFile, output);
console.log(`\nUnified Matrix generated at: ${outputFile}`);
