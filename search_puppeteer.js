const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

// Function to sanitize URLs for file naming
function sanitizeUrl(url) {
    const withoutProtocol = url.replace(/^https?:\/\//, '');
    const withoutTrailingSlash = withoutProtocol.replace(/\/$/, '');
    return withoutTrailingSlash.replace(/[\/:.]/g, '_');
}

// Function to download PDFs
async function downloadPDF(page, url, outputPath) {
    try {
        // Navigate to PDF URL
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
        
        // Wait for PDF content to load
        await page.waitForSelector('body', { timeout: 10000 });
        
        // Get the PDF content
        const pdfContent = await page.evaluate(() => {
            const iframe = document.querySelector('iframe');
            if (iframe) {
                return iframe.contentWindow.document.body.innerHTML;
            }
            return document.body.innerHTML;
        });
        
        // Save the PDF content
        fs.writeFileSync(outputPath, pdfContent);
        return true;
    } catch (error) {
        console.error(`Failed to download PDF from ${url}:`, error.message);
        return false;
    }
}

// Function to extract text from PDF
async function extractPDFText(filePath) {
    try {
        const data = await pdf(fs.readFileSync(filePath));
        return data.text;
    } catch (error) {
        console.error(`Failed to extract text from PDF:`, error.message);
        return '';
    }
}

(async () => {
    const browser = await puppeteer.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    const url = process.argv[2];

    try {
        console.log(`Navigating to URL: ${url}`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });

        // Extract all visible text from the page
        const pageText = await page.evaluate(() => document.body.innerText || '');
        if (!pageText) {
            throw new Error('Page content is empty');
        }

        // Extract emails
        const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,7}/g;
        const emails = pageText.match(emailPattern) || [];
        const emailLinks = await page.$$eval('a[href^="mailto:"]', links =>
            links.map(link => link.href.replace('mailto:', '').trim())
        );
        emails.push(...emailLinks);
        const uniqueEmails = [...new Set(emails)];

        // Extract phone numbers
        const phonePattern = /\+?[1-9]\d{1,2}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;
        const phones = pageText.match(phonePattern) || [];
        const cleanedPhones = phones.map(phone => phone.replace(/[-.\s]+/g, ' ').trim());
        const uniquePhones = [...new Set(cleanedPhones)];

        // Extract addresses
        const addressPattern = /\d{1,5}\s\w+(\s\w+)*,\s\w+(\s\w+)*,\s[A-Z]{2}\s\d{5}/g;
        const addresses = pageText.match(addressPattern) || [];
        const uniqueAddresses = [...new Set(addresses)];

        // Extract donation amounts
        const donationPattern = /\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?/g;
        const donations = pageText.match(donationPattern) || [];
        const uniqueDonations = [...new Set(donations)];

        // Extract PDF links
        const pdfLinks = await page.$$eval('a[href$=\".pdf\"]', links =>
            links.map(link => link.href)
        );
        const uniquePdfLinks = [...new Set(pdfLinks)];
        
        // Download and process PDFs
        const pdfData = [];
        const sanitizedUrl = sanitizeUrl(url);
        const directory = path.join(__dirname, `data/${sanitizedUrl}`);
        fs.mkdirSync(directory, { recursive: true });

        for (const pdfUrl of uniquePdfLinks) {
            try {
                const pdfPath = path.join(directory, `${sanitizeUrl(pdfUrl)}.pdf`);
                if (await downloadPDF(page, pdfUrl, pdfPath)) {
                    const pdfText = await extractPDFText(pdfPath);
                    if (pdfText) {
                        pdfData.push({
                            url: pdfUrl,
                            text: pdfText,
                            extracted: {
                                emails: pdfText.match(emailPattern) || [],
                                phones: pdfText.match(phonePattern) || [],
                                addresses: pdfText.match(addressPattern) || [],
                                donations: pdfText.match(donationPattern) || []
                            }
                        });
                    }
                }
            } catch (error) {
                console.error(`Failed processing PDF ${pdfUrl}:`, error.message);
            }
        }

        // Save extracted data with lists
        const data = {
            Emails: uniqueEmails,
            Phones: uniquePhones,
            Addresses: uniqueAddresses,
            Donations: uniqueDonations,
            PDFLinks: uniquePdfLinks,
            PDFData: pdfData,
            RawText: pageText,
            Donors: [] // Add empty Donors array to match expected structure
        };

        const dataPath = path.join(directory, 'extracted_data.json');
        fs.writeFileSync(dataPath, JSON.stringify(data, null, 2));
        console.log(`Extracted data saved to: ${dataPath}`);
    } catch (error) {
        console.error(`Error processing URL ${url}:`, error.message);
    } finally {
        await browser.close();
        console.log('Browser closed.');
    }
})();
