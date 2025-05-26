const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const config = require('./reveal_dom_config.json'); // Load the configuration file

(async () => {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    const url = process.argv[2];

    try {
        console.log(`Navigating to URL: ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });

        // Log all network requests
        page.on('response', async response => {
            console.log(`Response URL: ${response.url()}`);
            try {
                const text = await response.text();
                console.log(`Response Body: ${text.substring(0, 500)}...`); // Log first 500 characters
            } catch (err) {
                console.log(`Non-text response: ${response.url()}`);
            }
        });

        // Extract all visible text
        const pageText = await page.evaluate(() => document.body.innerText);
        console.log('Extracted page text:', pageText);

        // Extract emails
        let emails = [];
        if (config.emailSelector) {
            emails = await page.$$eval(config.emailSelector, links =>
                links.map(link => link.href.replace('mailto:', '').trim())
            );
        }
        console.log('Extracted emails:', [...new Set(emails)]);

        // Extract phone numbers
        let phones = [];
        if (config.phonePattern) {
            const phonePattern = new RegExp(config.phonePattern, 'g');
            phones = pageText.match(phonePattern) || [];
        }
        const cleanedPhones = phones.map(phone => phone.replace(/\s+/g, ' ').trim());
        console.log('Cleaned phones:', [...new Set(cleanedPhones)]);

        // Extract potential addresses
        let addresses = [];
        if (config.addressPattern) {
            const addressPattern = new RegExp(config.addressPattern, 'g');
            addresses = pageText.match(addressPattern) || [];
        }
        console.log('Extracted addresses:', addresses);

        // Extract PDF links
        let pdfLinks = [];
        if (config.pdfSelector) {
            pdfLinks = await page.$$eval(config.pdfSelector, links =>
                links.map(link => link.href)
            );
        }
        console.log('Extracted PDF links:', [...new Set(pdfLinks)]);

        // Extract hidden content
        const hiddenContent = await page.$$eval('[style*="display: none"], [style*="visibility: hidden"]', elements =>
            elements.map(el => el.innerText.trim()).filter(text => text)
        );
        console.log('Hidden content:', hiddenContent);

        // Log the DOM structure
        const domStructure = await page.evaluate(() => {
            const traverse = (node, depth = 0) => {
                const indent = '  '.repeat(depth);
                let structure = `${indent}<${node.tagName.toLowerCase()}`;
                for (const attr of node.attributes) {
                    structure += ` ${attr.name}="${attr.value}"`;
                }
                structure += '>';
                for (const child of node.children) {
                    structure += `\n${traverse(child, depth + 1)}`;
                }
                structure += `\n${indent}</${node.tagName.toLowerCase()}>`;
                return structure;
            };
            return traverse(document.body);
        });

        // Sanitize the URL to create a folder name (aligned with search115.py)
        const sanitizedUrl = url
            .replace(/^https?:\/\//, '') // Remove http:// or https://
            .replace(/\/$/, '')          // Remove trailing slash
            .replace(/[\/:.]/g, '_');    // Replace /, :, and . with _

        // Create the directory for the sanitized URL
        const directory = path.join(__dirname, `data/${sanitizedUrl}`);
        fs.mkdirSync(directory, { recursive: true }); // Ensure the directory exists

        // Save DOM structure
        const domStructurePath = path.join(directory, 'dom_structure.txt');
        fs.writeFileSync(domStructurePath, domStructure);
        console.log(`DOM structure saved to: ${domStructurePath}`);

        // Save full HTML
        const fullHtml = await page.evaluate(() => document.documentElement.outerHTML);
        const fullHtmlPath = path.join(directory, 'full_page.html');
        fs.writeFileSync(fullHtmlPath, fullHtml);
        console.log(`Full HTML saved to: ${fullHtmlPath}`);

        // Save all links
        const allLinks = await page.$$eval('a', links => links.map(link => link.href));
        const allLinksPath = path.join(directory, 'all_links.txt');
        fs.writeFileSync(allLinksPath, allLinks.join('\n'));
        console.log(`All links saved to: ${allLinksPath}`);

        // Save all scripts
        const allScripts = await page.$$eval('script', scripts =>
            scripts.map(script => script.src || 'inline script')
        );
        const allScriptsPath = path.join(directory, 'all_scripts.txt');
        fs.writeFileSync(allScriptsPath, allScripts.join('\n'));
        console.log(`All scripts saved to: ${allScriptsPath}`);

        // Save all stylesheets
        const allStylesheets = await page.$$eval('link[rel="stylesheet"]', links =>
            links.map(link => link.href)
        );
        const allStylesheetsPath = path.join(directory, 'all_stylesheets.txt');
        fs.writeFileSync(allStylesheetsPath, allStylesheets.join('\n'));
        console.log(`All stylesheets saved to: ${allStylesheetsPath}`);

        // Save extracted data
        const data = {
            Emails: [...new Set(emails)],
            Phones: [...new Set(cleanedPhones)],
            Addresses: [...new Set(addresses)],
            PDFLinks: [...new Set(pdfLinks)],
            HiddenContent: hiddenContent
        };
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const dataPath = path.join(directory, `extracted_data_${timestamp}.json`);
        fs.writeFileSync(dataPath, JSON.stringify(data, null, 2));
        console.log(`Extracted data saved to: ${dataPath}`);
    } catch (error) {
        console.error('Error:', error);
    } finally {
        await browser.close();
        console.log('Browser closed.');
    }
})();