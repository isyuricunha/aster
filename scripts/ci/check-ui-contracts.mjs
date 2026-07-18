import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const SCRIPT_DIRECTORY = path.dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = path.resolve(SCRIPT_DIRECTORY, "../..");
const DEFAULT_SOURCE_ROOT = path.join(REPOSITORY_ROOT, "apps", "web", "src", "app");
const MAX_REPORTED_LOCATIONS = 8;

function maskComments(source, { lineComments = false } = {}) {
  const characters = [...source];
  let state = "code";

  for (let index = 0; index < characters.length; index += 1) {
    const character = characters[index];
    const next = characters[index + 1];

    if (state === "block-comment") {
      if (character === "*" && next === "/") {
        characters[index] = " ";
        characters[index + 1] = " ";
        index += 1;
        state = "code";
      } else if (character !== "\n" && character !== "\r") {
        characters[index] = " ";
      }
      continue;
    }

    if (state === "line-comment") {
      if (character === "\n" || character === "\r") {
        state = "code";
      } else {
        characters[index] = " ";
      }
      continue;
    }

    if (state === "single-quote" || state === "double-quote" || state === "template") {
      const closingCharacter =
        state === "single-quote" ? "'" : state === "double-quote" ? '"' : "`";
      if (character === "\\") {
        index += 1;
      } else if (character === closingCharacter) {
        state = "code";
      }
      continue;
    }

    if (character === "/" && next === "*") {
      characters[index] = " ";
      characters[index + 1] = " ";
      index += 1;
      state = "block-comment";
    } else if (lineComments && character === "/" && next === "/") {
      characters[index] = " ";
      characters[index + 1] = " ";
      index += 1;
      state = "line-comment";
    } else if (character === "'") {
      state = "single-quote";
    } else if (character === '"') {
      state = "double-quote";
    } else if (character === "`") {
      state = "template";
    }
  }

  return characters.join("");
}

function locationAt(source, index) {
  const before = source.slice(0, index);
  const line = before.split(/\r?\n/).length;
  const lastLineBreak = Math.max(before.lastIndexOf("\n"), before.lastIndexOf("\r"));
  return { line, column: index - lastLineBreak };
}

function canonicalPath(filePath) {
  const resolved = path.resolve(filePath);
  return process.platform === "win32" ? resolved.toLowerCase() : resolved;
}

function escapeRegularExpression(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isSourceFile(filePath) {
  return /\.(?:css|tsx?|jsx?)$/i.test(filePath);
}

async function collectFiles(directory) {
  const collected = [];
  const entries = await readdir(directory, { withFileTypes: true });

  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      collected.push(...(await collectFiles(entryPath)));
    } else if (entry.isFile() && isSourceFile(entryPath)) {
      collected.push({ path: entryPath, content: await readFile(entryPath, "utf8") });
    }
  }

  return collected;
}

function collectCustomPropertyDefinitions(files) {
  const definitions = new Set();

  for (const file of files) {
    const isCss = file.path.endsWith(".css");
    const source = maskComments(file.content, { lineComments: !isCss });
    const declarationPattern = /(--[A-Za-z_][\w-]*)\s*:/g;
    const propertyRulePattern = /@property\s+(--[A-Za-z_][\w-]*)/g;
    const objectPropertyPattern = /["'`](--[A-Za-z_][\w-]*)["'`]\s*:/g;
    const setPropertyPattern = /setProperty\s*\(\s*["'`](--[A-Za-z_][\w-]*)["'`]/g;
    const variableOptionPattern = /\bvariable\s*:\s*["'`](--[A-Za-z_][\w-]*)["'`]/g;

    for (const match of source.matchAll(declarationPattern)) {
      definitions.add(match[1]);
    }
    for (const match of source.matchAll(propertyRulePattern)) {
      definitions.add(match[1]);
    }
    if (!isCss) {
      for (const match of source.matchAll(objectPropertyPattern)) {
        definitions.add(match[1]);
      }
      for (const match of source.matchAll(setPropertyPattern)) {
        definitions.add(match[1]);
      }
      for (const match of source.matchAll(variableOptionPattern)) {
        definitions.add(match[1]);
      }
    }
  }

  return definitions;
}

function analyzeCustomProperties(files) {
  const definitions = collectCustomPropertyDefinitions(files);
  const issues = [];
  let usageCount = 0;
  let fallbackCount = 0;

  for (const file of files) {
    const isCss = file.path.endsWith(".css");
    const source = maskComments(file.content, { lineComments: !isCss });
    const usagePattern = /var\(\s*(--[A-Za-z_][\w-]*)\s*(,|\))/g;

    for (const match of source.matchAll(usagePattern)) {
      usageCount += 1;
      if (match[2] === ",") {
        fallbackCount += 1;
        continue;
      }
      if (!definitions.has(match[1])) {
        issues.push({
          type: "undefined-custom-property",
          name: match[1],
          filePath: file.path,
          ...locationAt(file.content, match.index),
        });
      }
    }
  }

  return { definitions, issues, usageCount, fallbackCount };
}

function extractCssModuleClasses(source) {
  const withoutComments = maskComments(source);
  const withoutGlobals = withoutComments.replace(/:global\([^)]*\)/g, (match) =>
    match.replace(/[^\r\n]/g, " "),
  );
  const classes = new Set();
  const classPattern = /\.([A-Za-z_][\w-]*)/g;

  for (const match of withoutGlobals.matchAll(classPattern)) {
    classes.add(match[1]);
  }

  return classes;
}

function templateClassPattern(template) {
  const expressionPattern = /\$\{[^{}]+\}/g;
  let cursor = 0;
  let expressionCount = 0;
  let pattern = "^";

  for (const match of template.matchAll(expressionPattern)) {
    expressionCount += 1;
    pattern += escapeRegularExpression(template.slice(cursor, match.index));
    pattern += "[A-Za-z0-9_-]+";
    cursor = match.index + match[0].length;
  }

  if (expressionCount === 0) return null;
  pattern += escapeRegularExpression(template.slice(cursor));
  pattern += "$";

  return {
    expression: new RegExp(pattern),
    display: template.replace(expressionPattern, "*"),
  };
}

function resolveCssModule(importerPath, specifier) {
  if (!specifier.startsWith(".")) return null;
  return path.resolve(path.dirname(importerPath), specifier);
}

function analyzeCssModules(files) {
  const moduleFiles = new Map();
  const issues = [];
  let referenceCount = 0;
  let dynamicLookupCount = 0;

  for (const file of files) {
    if (file.path.endsWith(".module.css")) {
      moduleFiles.set(canonicalPath(file.path), {
        ...file,
        classes: extractCssModuleClasses(file.content),
      });
    }
  }

  for (const file of files) {
    if (!/\.(?:tsx?|jsx?)$/i.test(file.path)) continue;

    const importPattern = /\bimport\s+([A-Za-z_$][\w$]*)\s+from\s+["']([^"']+\.module\.css)["']/g;
    for (const importMatch of file.content.matchAll(importPattern)) {
      const alias = importMatch[1];
      const specifier = importMatch[2];
      const resolvedPath = resolveCssModule(file.path, specifier);
      if (!resolvedPath) continue;

      const moduleFile = moduleFiles.get(canonicalPath(resolvedPath));
      if (!moduleFile) {
        issues.push({
          type: "missing-css-module",
          filePath: file.path,
          specifier,
          ...locationAt(file.content, importMatch.index),
        });
        continue;
      }

      const aliasPattern = escapeRegularExpression(alias);
      const dotPattern = new RegExp(`\\b${aliasPattern}\\.([A-Za-z_$][\\w$]*)`, "g");
      const bracketPattern = new RegExp(
        `\\b${aliasPattern}\\s*\\[\\s*(["'\\x60])([^"'\\x60\\r\\n]+)\\1\\s*\\]`,
        "g",
      );
      const resolvedRanges = [];

      for (const accessMatch of file.content.matchAll(dotPattern)) {
        referenceCount += 1;
        const className = accessMatch[1];
        if (!moduleFile.classes.has(className)) {
          issues.push({
            type: "missing-css-module-class",
            name: className,
            filePath: file.path,
            modulePath: moduleFile.path,
            ...locationAt(file.content, accessMatch.index),
          });
        }
      }

      for (const accessMatch of file.content.matchAll(bracketPattern)) {
        referenceCount += 1;
        resolvedRanges.push([accessMatch.index, accessMatch.index + accessMatch[0].length]);
        const classExpression = accessMatch[2];
        const templatePattern =
          accessMatch[1] === "`" ? templateClassPattern(classExpression) : null;

        if (templatePattern) {
          const hasMatchingClass = [...moduleFile.classes].some((className) =>
            templatePattern.expression.test(className),
          );
          if (!hasMatchingClass) {
            issues.push({
              type: "missing-css-module-template",
              name: templatePattern.display,
              filePath: file.path,
              modulePath: moduleFile.path,
              ...locationAt(file.content, accessMatch.index),
            });
          }
        } else if (!moduleFile.classes.has(classExpression)) {
          issues.push({
            type: "missing-css-module-class",
            name: classExpression,
            filePath: file.path,
            modulePath: moduleFile.path,
            ...locationAt(file.content, accessMatch.index),
          });
        }
      }

      const anyBracketPattern = new RegExp(`\\b${aliasPattern}\\s*\\[[^\\]\r\n]+\\]`, "g");
      for (const dynamicMatch of file.content.matchAll(anyBracketPattern)) {
        const wasResolved = resolvedRanges.some(
          ([start, end]) => dynamicMatch.index >= start && dynamicMatch.index < end,
        );
        if (!wasResolved) dynamicLookupCount += 1;
      }
    }
  }

  return { issues, referenceCount, dynamicLookupCount, moduleCount: moduleFiles.size };
}

function analyzeFiles(files) {
  const customProperties = analyzeCustomProperties(files);
  const cssModules = analyzeCssModules(files);
  return {
    issues: [...customProperties.issues, ...cssModules.issues],
    customProperties,
    cssModules,
  };
}

function relativePath(filePath) {
  const relative = path.relative(REPOSITORY_ROOT, filePath);
  return relative && !relative.startsWith("..") ? relative : filePath;
}

function reportIssues(result) {
  const customPropertyIssues = result.issues.filter(
    (issue) => issue.type === "undefined-custom-property",
  );
  const moduleIssues = result.issues.filter((issue) => issue.type !== "undefined-custom-property");

  console.error(`UI contract check failed with ${result.issues.length} violation(s).`);

  if (customPropertyIssues.length > 0) {
    console.error("\nUndefined CSS custom properties:");
    const grouped = Map.groupBy(customPropertyIssues, (issue) => issue.name);
    for (const [name, issues] of [...grouped.entries()].sort(([left], [right]) =>
      left.localeCompare(right),
    )) {
      console.error(`  ${name} is used without a declaration or explicit fallback:`);
      for (const issue of issues.slice(0, MAX_REPORTED_LOCATIONS)) {
        console.error(`    ${relativePath(issue.filePath)}:${issue.line}:${issue.column}`);
      }
      if (issues.length > MAX_REPORTED_LOCATIONS) {
        console.error(`    ...and ${issues.length - MAX_REPORTED_LOCATIONS} more occurrence(s)`);
      }
    }
  }

  if (moduleIssues.length > 0) {
    console.error("\nCSS Module contract violations:");
    for (const issue of moduleIssues.sort((left, right) =>
      `${left.filePath}:${left.line}`.localeCompare(`${right.filePath}:${right.line}`),
    )) {
      const source = `${relativePath(issue.filePath)}:${issue.line}:${issue.column}`;
      if (issue.type === "missing-css-module") {
        console.error(`  ${source} cannot resolve CSS Module import ${JSON.stringify(issue.specifier)}`);
      } else if (issue.type === "missing-css-module-template") {
        console.error(
          `  ${source} uses dynamic class pattern ${JSON.stringify(issue.name)}, but ${relativePath(issue.modulePath)} exports no matching class`,
        );
      } else {
        console.error(
          `  ${source} references ${JSON.stringify(issue.name)}, but ${relativePath(issue.modulePath)} does not export that class`,
        );
      }
    }
  }

  console.error(
    "\nDeclare the token, add an explicit var(--token, fallback), or align the TSX reference with an exported CSS Module class.",
  );
}

function assertSelfTest(condition, message, state) {
  state.assertions += 1;
  if (!condition) throw new Error(`Self-test failed: ${message}`);
}

function runSelfTest() {
  const fixtureRoot = path.resolve(REPOSITORY_ROOT, ".ui-contract-self-test");
  const passingFiles = [
    {
      path: path.join(fixtureRoot, "theme.css"),
      content: `
        :root { --declared: #fff; }
        @property --registered { syntax: "<color>"; initial-value: red; inherits: true; }
        .sample {
          color: var(--declared);
          border-color: var(--registered);
          background: var(--external-token, transparent);
        }
      `,
    },
    {
      path: path.join(fixtureRoot, "sample.module.css"),
      content: ".known {} .bracket-name {} .status_ready {} :global(.external) {}",
    },
    {
      path: path.join(fixtureRoot, "sample.tsx"),
      content: `
        import styles from "./sample.module.css";
        const font = loadFont({ variable: "--runtime-font" });
        const inlineStyle = { "--inline-token": "#fff", color: "var(--inline-token)" };
        const state = "ready";
        export const Sample = () => (
          <div className={\`${"${font.variable}"} ${"${styles.known}"} ${"${styles[\"bracket-name\"]}"} ${"${styles[`status_${state}`]}"}\`} style={{ ...inlineStyle, fontFamily: "var(--runtime-font)" }} />
        );
      `,
    },
  ];
  const failingFiles = [
    {
      path: path.join(fixtureRoot, "failure.css"),
      content: ".failure { color: var(--missing-token); background: var(--allowed, red); }",
    },
    {
      path: path.join(fixtureRoot, "failure.module.css"),
      content: ".known {}",
    },
    {
      path: path.join(fixtureRoot, "failure.tsx"),
      content: `
        import styles from "./failure.module.css";
        const state = "ready";
        export const Failure = () => (
          <div className={\`${"${styles.missing}"} ${"${styles[\"also-missing\"]}"} ${"${styles[`phase_${state}`]}"} ${"${styles[state]}"}\`} />
        );
      `,
    },
  ];

  const passingResult = analyzeFiles(passingFiles);
  const failingResult = analyzeFiles(failingFiles);
  const state = { assertions: 0 };

  assertSelfTest(passingResult.issues.length === 0, "valid contracts should pass", state);
  assertSelfTest(
    passingResult.customProperties.fallbackCount === 1,
    "explicit custom-property fallbacks should be ignored",
    state,
  );
  assertSelfTest(
    passingResult.cssModules.referenceCount === 3,
    "dot, bracket, and template CSS Module references should be checked",
    state,
  );
  assertSelfTest(
    failingResult.customProperties.issues.length === 1 &&
      failingResult.customProperties.issues[0].name === "--missing-token",
    "undefined custom properties should fail",
    state,
  );
  assertSelfTest(
    failingResult.cssModules.issues.filter((issue) => issue.type === "missing-css-module-class")
      .length === 2,
    "missing dot and bracket classes should fail",
    state,
  );
  assertSelfTest(
    failingResult.cssModules.issues.some(
      (issue) => issue.type === "missing-css-module-template" && issue.name === "phase_*",
    ),
    "unmatched dynamic template class families should fail",
    state,
  );
  assertSelfTest(
    failingResult.cssModules.dynamicLookupCount === 1,
    "fully dynamic class lookups should be skipped conservatively",
    state,
  );

  console.log(`UI contract self-test passed (${state.assertions} assertions).`);
}

async function main() {
  const argumentsList = process.argv.slice(2);
  if (argumentsList.includes("--self-test")) {
    runSelfTest();
    return;
  }
  if (argumentsList.length > 0) {
    throw new Error(`Unknown argument(s): ${argumentsList.join(" ")}`);
  }

  const files = await collectFiles(DEFAULT_SOURCE_ROOT);
  const result = analyzeFiles(files);
  if (result.issues.length > 0) {
    reportIssues(result);
    process.exitCode = 1;
    return;
  }

  const cssFileCount = files.filter((file) => file.path.endsWith(".css")).length;
  const componentFileCount = files.length - cssFileCount;
  console.log(
    `UI contract check passed (${cssFileCount} CSS files, ${componentFileCount} component files, ${result.customProperties.definitions.size} custom properties, ${result.cssModules.referenceCount} CSS Module references).`,
  );
  if (result.cssModules.dynamicLookupCount > 0) {
    console.log(
      `Skipped ${result.cssModules.dynamicLookupCount} fully dynamic CSS Module lookup(s) that cannot be resolved statically.`,
    );
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
