const esbuild = require('esbuild');
const path = require('path');
const fs = require('fs');

const isWatch = process.argv.includes('--watch');

// Plugin to resolve @/ path aliases
const aliasPlugin = {
  name: 'alias',
  setup(build) {
    // Resolve @/ to static/src/
    build.onResolve({ filter: /^@\// }, (args) => {
      const relativePath = args.path.replace(/^@\//, '');
      const basePath = path.resolve(__dirname, 'static/src', relativePath);
      
      // Try different extensions
      const extensions = ['', '.tsx', '.ts', '.js', '.jsx'];
      for (const ext of extensions) {
        const fullPath = basePath + ext;
        if (fs.existsSync(fullPath)) {
          return { path: fullPath };
        }
      }
      
      // Try index files
      const indexExtensions = ['/index.tsx', '/index.ts', '/index.js'];
      for (const ext of indexExtensions) {
        const fullPath = basePath + ext;
        if (fs.existsSync(fullPath)) {
          return { path: fullPath };
        }
      }
      
      return { path: basePath };
    });
  },
};

const buildOptions = {
  entryPoints: ['static/src/islands.tsx'],
  bundle: true,
  minify: !isWatch,
  sourcemap: isWatch,
  outfile: 'static/js/islands.js',
  jsx: 'automatic',
  target: ['es2020'],
  format: 'iife',
  loader: {
    '.tsx': 'tsx',
    '.ts': 'ts',
    '.css': 'css',
  },
  define: {
    'process.env.NODE_ENV': isWatch ? '"development"' : '"production"',
  },
  plugins: [aliasPlugin],
};

if (isWatch) {
  esbuild.context(buildOptions).then((ctx) => {
    ctx.watch();
    console.log('Watching for changes...');
  });
} else {
  esbuild.build(buildOptions).then(() => {
    console.log('Build complete');
  });
}
