#!/usr/bin/env node
/**
 * Simple Mobile App Test
 * Tests the core React Native setup without complex dependencies
 */

const fs = require('fs');
const path = require('path');

function testMobileAppStructure() {
    console.log('🧪 Testing mobile app structure...');

    const mobileDir = 'remi-mobile';
    const requiredFiles = [
        'package.json',
        'App.tsx',
        'src/components',
        'src/services',
        'src/screens',
        'src/navigation'
    ];

    let passed = 0;
    let failed = 0;

    for (const file of requiredFiles) {
        const filePath = path.join(mobileDir, file);
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

function testMobileAppConfig() {
    console.log('🧪 Testing mobile app configuration...');

    try {
        const packagePath = path.join('remi-mobile', 'package.json');
        const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

        console.log(`✅ Package name: ${packageJson.name}`);
        console.log(`✅ Version: ${packageJson.version}`);

        // Check key dependencies
        const keyDeps = ['react', 'react-native', '@react-navigation/native', '@tanstack/react-query'];
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

function testMobileAppComponents() {
    console.log('🧪 Testing mobile app components...');

    const componentsDir = path.join('remi-mobile', 'src', 'components');

    if (!fs.existsSync(componentsDir)) {
        console.log('❌ Components directory missing');
        return false;
    }

    const components = fs.readdirSync(componentsDir);
    const keyComponents = [
        'ContactSearchInput.tsx',
        'ContactSearchResults.tsx',
        'ContactCard.tsx'
    ];

    let componentsFound = 0;
    for (const component of keyComponents) {
        if (components.includes(component)) {
            console.log(`✅ ${component} found`);
            componentsFound++;
        } else {
            console.log(`⚠️  ${component} not found`);
        }
    }

    console.log(`✅ Found ${components.length} total components`);
    return componentsFound >= 2; // At least 2 key components
}

function testMobileAppServices() {
    console.log('🧪 Testing mobile app services...');

    const servicesDir = path.join('remi-mobile', 'src', 'services');

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
    console.log('🚀 Starting R.E.M.I Mobile App Tests');
    console.log('=' * 50);

    const tests = [
        { name: 'App Structure', func: testMobileAppStructure },
        { name: 'App Configuration', func: testMobileAppConfig },
        { name: 'App Components', func: testMobileAppComponents },
        { name: 'App Services', func: testMobileAppServices }
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

    console.log(`\n📊 Mobile App Test Summary:`);
    console.log(`   Passed: ${passed}`);
    console.log(`   Failed: ${failed}`);
    console.log(`   Total:  ${passed + failed}`);

    if (failed === 0) {
        console.log('🎉 All mobile app tests passed!');
        return 0;
    } else {
        console.log('💥 Some mobile app tests failed!');
        return 1;
    }
}

if (require.main === module) {
    process.exit(main());
}