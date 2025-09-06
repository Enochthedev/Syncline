#!/usr/bin/env node
/**
 * Simple Web App Test
 * Tests the core Next.js setup without complex dependencies
 */

const fs = require('fs');
const path = require('path');

function testWebAppStructure() {
    console.log('🧪 Testing web app structure...');

    const webDir = 'remi-web';
    const requiredFiles = [
        'package.json',
        'next.config.js',
        'src/app',
        'src/components',
        'src/services',
        'src/hooks'
    ];

    let passed = 0;
    let failed = 0;

    for (const file of requiredFiles) {
        const filePath = path.join(webDir, file);
        if (fs.existsSync(filePath)) {
            console.log(`✅ ${file} exists`);
            passed++;
        } else {
            console.log(`❌ ${file} missing`);
            failed++;
        }
    }

    return failed === 0;
}

function testWebAppConfig() {
    console.log('🧪 Testing web app configuration...');

    try {
        const packagePath = path.join('remi-web', 'package.json');
        const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

        console.log(`✅ Package name: ${packageJson.name}`);
        console.log(`✅ Version: ${packageJson.version}`);

        // Check key dependencies
        const keyDeps = ['react', 'react-dom', 'next', '@tanstack/react-query'];
        let depsOk = true;

        for (const dep of keyDeps) {
            if (packageJson.dependencies[dep]) {
                console.log(`✅ ${dep}: ${packageJson.dependencies[dep]}`);
            } else {
                console.log(`❌ ${dep} missing`);
                depsOk = false;
            }
        }

        return depsOk;
    } catch (error) {
        console.log(`❌ Failed to read package.json: ${error.message}`);
        return false;
    }
}

function testWebAppComponents() {
    console.log('🧪 Testing web app components...');

    const componentsDir = path.join('remi-web', 'src', 'components');

    if (!fs.existsSync(componentsDir)) {
        console.log('❌ Components directory missing');
        return false;
    }

    // Count components recursively
    function countComponents(dir) {
        let count = 0;
        const items = fs.readdirSync(dir);

        for (const item of items) {
            const itemPath = path.join(dir, item);
            const stat = fs.statSync(itemPath);

            if (stat.isDirectory()) {
                count += countComponents(itemPath);
            } else if (item.endsWith('.tsx') || item.endsWith('.ts')) {
                count++;
            }
        }

        return count;
    }

    const componentCount = countComponents(componentsDir);
    console.log(`✅ Found ${componentCount} component files`);

    // Check for key components
    const keyComponents = [
        'ContactSearchInput.tsx',
        'IntegratedSearchWorkflow.tsx'
    ];

    let keyComponentsFound = 0;
    function findComponents(dir, components) {
        const items = fs.readdirSync(dir);

        for (const item of items) {
            const itemPath = path.join(dir, item);
            const stat = fs.statSync(itemPath);

            if (stat.isDirectory()) {
                findComponents(itemPath, components);
            } else if (components.includes(item)) {
                console.log(`✅ ${item} found`);
                keyComponentsFound++;
            }
        }
    }

    findComponents(componentsDir, keyComponents);

    return componentCount >= 5; // At least 5 components
}

function testWebAppPages() {
    console.log('🧪 Testing web app pages...');

    const appDir = path.join('remi-web', 'src', 'app');

    if (!fs.existsSync(appDir)) {
        console.log('❌ App directory missing');
        return false;
    }

    const requiredFiles = ['layout.tsx', 'page.tsx'];
    let filesFound = 0;

    for (const file of requiredFiles) {
        const filePath = path.join(appDir, file);
        if (fs.existsSync(filePath)) {
            console.log(`✅ ${file} found`);
            filesFound++;
        } else {
            console.log(`⚠️  ${file} not found`);
        }
    }

    return filesFound >= 1; // At least one key file
}

function testWebAppServices() {
    console.log('🧪 Testing web app services...');

    const servicesDir = path.join('remi-web', 'src', 'services');

    if (!fs.existsSync(servicesDir)) {
        console.log('❌ Services directory missing');
        return false;
    }

    const services = fs.readdirSync(servicesDir);
    const keyServices = [
        'authService.ts',
        'apiClient.ts',
        'unifiedBusinessLogic.ts'
    ];

    let servicesFound = 0;
    for (const service of keyServices) {
        if (services.includes(service)) {
            console.log(`✅ ${service} found`);
            servicesFound++;
        } else {
            console.log(`⚠️  ${service} not found`);
        }
    }

    console.log(`✅ Found ${services.length} total services`);
    return servicesFound >= 2; // At least 2 key services
}

function main() {
    console.log('🚀 Starting R.E.M.I Web App Tests');
    console.log('=' * 50);

    const tests = [
        { name: 'App Structure', func: testWebAppStructure },
        { name: 'App Configuration', func: testWebAppConfig },
        { name: 'App Components', func: testWebAppComponents },
        { name: 'App Pages', func: testWebAppPages },
        { name: 'App Services', func: testWebAppServices }
    ];

    let passed = 0;
    let failed = 0;

    for (const test of tests) {
        console.log(`\n📋 Running ${test.name} test...`);
        try {
            if (test.func()) {
                console.log(`✅ ${test.name} test PASSED`);
                passed++;
            } else {
                console.log(`❌ ${test.name} test FAILED`);
                failed++;
            }
        } catch (error) {
            console.log(`❌ ${test.name} test FAILED with error: ${error.message}`);
            failed++;
        }
    }

    console.log(`\n📊 Web App Test Summary:`);
    console.log(`   Passed: ${passed}`);
    console.log(`   Failed: ${failed}`);
    console.log(`   Total:  ${passed + failed}`);

    if (failed === 0) {
        console.log('🎉 All web app tests passed!');
        return 0;
    } else {
        console.log('💥 Some web app tests failed!');
        return 1;
    }
}

if (require.main === module) {
    process.exit(main());
}