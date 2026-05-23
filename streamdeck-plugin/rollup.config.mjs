import commonjs from '@rollup/plugin-commonjs';
import nodeResolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';

/** @type {import('rollup').RollupOptions} */
const config = {
  input: 'src/plugin.ts',
  output: {
    file: 'com.shadowbridge.app.sdPlugin/bin/plugin.js',
    format: 'cjs',
    sourcemap: false,
    exports: 'auto',
  },
  plugins: [
    typescript(),
    nodeResolve({ preferBuiltins: true, exportConditions: ['node'] }),
    commonjs(),
  ],
  external: ['canvas'],
};

export default config;
