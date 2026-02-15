const fs = require('fs');
const path = require('path');

const src = path.join(
    process.env.HOME,
    '.gemini/antigravity/brain/2ade3960-5334-4195-b1ab-f6e08dae963e/lady_justice_gold_1771090130276.png'
);
const dest = path.join(__dirname, 'public', 'lady-justice.png');

fs.copyFileSync(src, dest);
console.log('Copied to', dest);
console.log('Size:', fs.statSync(dest).size, 'bytes');
