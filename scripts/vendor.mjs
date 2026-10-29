import {mkdirSync,copyFileSync} from 'node:fs';
mkdirSync('web/vendor',{recursive:true});
for (const [source,target] of [['build/three.module.js','three.module.js'],['build/three.core.js','three.core.js'],['examples/jsm/controls/OrbitControls.js','OrbitControls.js'],['LICENSE','THREE-LICENSE.txt']]) copyFileSync('node_modules/three/'+source,'web/vendor/'+target);
