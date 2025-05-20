const fs = require("fs");
const path = require("path");

const name = process.argv[2];
if (!name) {
  console.error("❌ Fournis un nom de page !");
  process.exit(1);
}

const dir = path.join("src", "pages", name);
fs.mkdirSync(dir, { recursive: true });

fs.writeFileSync(path.join(dir, `${name}.tsx`), 
`import React from "react";
import styles from "./${name}.module.scss";

const ${name} = () => {
  return <div className={styles.container}>${name} page</div>;
};

export default ${name};`);

fs.writeFileSync(path.join(dir, `${name}.module.scss`), `.container {\n  padding: 1rem;\n}`);

fs.writeFileSync(path.join(dir, `index.ts`), `export { default } from "./${name}";`);

console.log(`✅ Page ${name} créée avec succès.`);
