import * as T from "three";
import {OrbitControls} from "three/addons/controls/OrbitControls.js";

export const ROLE_COLORS = [
  "#d6b975","#9cc8a9","#9dbdbd","#a6b6d5","#d3a399","#a4c7bd","#b1b9db",
  "#caafce","#d9be9a","#9fb9d7","#d8b3a4","#c0c8a0","#acd0a4"
];

const DESKS = [
  [0,-6.25],[-9.9,-5.7],[-6.7,-5.7],[-9.9,-1.5],[-6.7,-1.5],
  [6.55,-5.7],[9.9,-5.7],[6.55,-1.5],[9.9,-1.5],[6.55,2.7],
  [9.9,2.7],[-9.9,2.7],[-6.7,2.7]
];
const ROOM_Z = -.5;
const UP = new T.Vector3(0,1,0);
const CENTER = new T.Vector3(0,0,.32);
const DETAIL = new T.Vector3();
const PROJECTED = new T.Vector3();
const VIEWS = {
  research: [-8.05,.30,-1.7,1.70],
  "war-room": [0,.35,-.38,1.77],
  production: [8.28,.30,-1.7,1.71],
  lounge: [0,.22,6.35,1.77]
};

function material(color, roughness = .8, extras = {}) {
  return new T.MeshStandardMaterial({color, roughness, ...extras});
}

function canvasTexture(width, height, draw) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  draw(canvas.getContext("2d"), width, height);
  const texture = new T.CanvasTexture(canvas);
  texture.colorSpace = T.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function woodFinish() {
  return canvasTexture(768, 512, (g,w,h) => {
    let seed = 816;
    const random = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let y=0; y<h; y+=22) {
      for (let x=-(y % 66) * 3; x<w; x+=132) {
        const light = 62 + random()*12;
        g.fillStyle = `hsl(${32 + random()*7} 29% ${light}%)`;
        g.fillRect(x,y,131,21);
        g.fillStyle = "#735b411c";
        for (let i=0; i<12; i++) g.fillRect(x+random()*125,y+random()*21,2+random()*72,.65);
      }
    }
  });
}

function titleTexture(text, color, paper = "#f0ede0") {
  return canvasTexture(384, 108, (g,w,h) => {
    g.fillStyle = paper;
    g.fillRect(0,0,w,h);
    g.fillStyle = color;
    g.font = "700 36px system-ui";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(text,w/2,h/2,w-28);
  });
}

function windowFinish(index) {
  return canvasTexture(384,144,(g,w,h)=>{
    const sky=g.createLinearGradient(0,0,0,h);
    sky.addColorStop(0,"#91b1b0");
    sky.addColorStop(1,"#e0d8aa");
    g.fillStyle=sky;
    g.fillRect(0,0,w,h);
    for (let x=-10;x<w;x+=29) {
      const tile=x+index*38;
      const rise=13+Math.abs(Math.sin(tile*.29))*42;
      g.fillStyle=tile%3===0?"#627975":"#81918a";
      g.fillRect(x,h-rise,24,rise);
      g.fillStyle="#c3b891";
      for (let y=h-rise+7;y<h-3;y+=11) g.fillRect(x+6,y,13,2);
    }
    g.fillStyle="#dce8d879";
    g.beginPath();
    g.moveTo(85,0); g.lineTo(145,0); g.lineTo(230,h); g.lineTo(174,h); g.closePath();
    g.fill();
  });
}

function weaveFinish() {
  return canvasTexture(96,96,(g,w,h)=>{
    g.fillStyle="#b8b29c";
    g.fillRect(0,0,w,h);
    for (let at=0;at<w;at+=4) {
      g.fillStyle=at%8===0?"#968b7572":"#ece0bf96";
      g.fillRect(at,0,1,h);
      g.fillRect(0,at,w,1);
    }
  });
}

function screenFinish(kind) {
  return canvasTexture(256, 160, (g,w,h) => {
    g.fillStyle = "#192c2c";
    g.fillRect(0,0,w,h);
    g.fillStyle = "#385454";
    g.fillRect(0,0,w,19);
    for (let x=8; x<29; x+=8) {
      g.fillStyle = x === 8 ? "#dfb181" : "#91bca5";
      g.fillRect(x,7,4,4);
    }
    if (kind % 3 === 0) {
      for (let y=30; y<145; y+=19) {
        g.fillStyle = "#476269";
        g.fillRect(14,y,43,10);
        g.fillStyle = "#98c7a9";
        g.fillRect(67,y+2,Math.min(176,80+(y*23)%116),5);
      }
    } else if (kind % 3 === 1) {
      g.fillStyle = "#57736b";
      g.fillRect(15,30,145,83);
      g.fillStyle = "#83b29e";
      g.fillRect(25,48,56,50);
      g.fillStyle = "#d5c18a";
      g.fillRect(90,55,56,35);
      for (let y=37; y<110; y+=14) g.fillRect(171,y,68-y%14,3);
      g.fillStyle = "#86bcac";
      g.fillRect(14,122,225,9);
      g.fillStyle = "#c2a981";
      g.fillRect(14,137,159,8);
    } else {
      for (let x=23; x<243; x+=22) {
        const bar = 21+(x*29)%81;
        g.fillStyle = x%3 === 0 ? "#dcb879" : "#76b09c";
        g.fillRect(x,136-bar,12,bar);
      }
    }
  });
}

export function buildOffice(host, roles, onPick) {
  const scene = new T.Scene();
  const camera = new T.OrthographicCamera(-17,17,12,-12,.1,200);
  const renderer = new T.WebGLRenderer({alpha:true,antialias:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFShadowMap;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.20;
  renderer.domElement.setAttribute("aria-label","Evolve HQ studio floor");
  host.append(renderer.domElement);
  const labels=document.createElement("div");
  labels.className="scene-labels";
  labels.setAttribute("aria-hidden","true");
  host.append(labels);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = .085;
  controls.enablePan = false;
  controls.minZoom = .64;
  controls.maxZoom = 2.45;
  controls.minPolarAngle = .31;
  controls.maxPolarAngle = 1.30;
  controls.target.copy(CENTER);

  const ambient = new T.HemisphereLight("#fff5d8","#7e8e80",2.14);
  const key = new T.DirectionalLight("#ffe2ad",2.9);
  key.position.set(11,19,4);
  key.castShadow = true;
  key.shadow.mapSize.set(2048,2048);
  Object.assign(key.shadow.camera,{left:-20,right:20,top:16,bottom:-16,near:1,far:55});
  key.shadow.normalBias = .035;
  key.shadow.bias = -.00012;
  const bounce = new T.DirectionalLight("#a4c8e2",1.05);
  bounce.position.set(-10,9,-13);
  scene.add(ambient,key,bounce);

  const unit = new T.BoxGeometry();
  const ball = new T.SphereGeometry(1,13,9);
  const cylinder = new T.CylinderGeometry(1,1,1,20);
  const slim = new T.CylinderGeometry(1,.87,1,12);
  const floor = material("#ffffff",.73,{map:woodFinish()});
  const oak = material("#a56a42",.57);
  const ash = material("#e2bf88",.64);
  const cream = material("#ede2ca");
  const wall = material("#dedac7");
  const dark = material("#333f38",.52);
  const ink = material("#263732",.57);
  const chrome = material("#7c8175",.44,{metalness:.27});
  const slate = material("#56726b");
  const moss = material("#80906e");
  const pale = material("#c4d0b1");
  const tiles = material("#dedac5");
  const warm = material("#b88060");
  const brass = material("#bba36b",.43,{metalness:.22});
  const glass = material("#abd2c1",.1,{transparent:true,opacity:.19,depthWrite:false});
  const paper = material("#f5e9c9");
  const books = [moss,warm,slate,cream,brass];
  const black = material("#26312f");
  const light = new T.MeshBasicMaterial({color:"#fff1b4"});
  const rug = material("#9aa795");
  const deskRugs=["#a8ac88","#a3aa92","#a6b4ad"].map(color=>material(color,.95));
  const roomRug=material("#818772",.89,{map:weaveFinish()});
  const walnut=material("#78543f",.47);
  const leaves = ["#466959","#537862","#7e9064"].map(color => material(color));

  function mesh(geometry, paint, x,y,z,sx,sy,sz,parent=scene, cast=true) {
    const obj = new T.Mesh(geometry,paint);
    obj.position.set(x,y,z);
    obj.scale.set(sx,sy,sz);
    obj.castShadow = cast;
    obj.receiveShadow = true;
    parent.add(obj);
    return obj;
  }
  const box = (paint,x,y,z,w,h,d,parent,cast) => mesh(unit,paint,x,y,z,w,h,d,parent,cast);
  const bulb = (paint,x,y,z,w,h,d,parent,cast) => mesh(ball,paint,x,y,z,w,h,d,parent,cast);
  const round = (paint,x,y,z,w,h,d,parent,cast) => mesh(cylinder,paint,x,y,z,w,h,d,parent,cast);
  function group(x,y,z) {
    const result = new T.Group();
    result.position.set(x,y,z);
    scene.add(result);
    return result;
  }

  box(dark,0,-.39,0,25.3,.53,17.25);
  box(cream,0,-.14,0,25.18,.17,17.12);
  box(floor,0,-.035,0,24.95,.08,16.94,scene,false);
  box(dark,0,-.172,8.61,25.15,.12,.10);
  box(dark,12.59,-.172,0,.10,.12,17.23);
  box(wall,0,1.11,-8.43,25.23,2.22,.26);
  box(wall,-12.48,.98,0,.25,1.98,17.12);
  box(oak,0,.18,-8.25,24.65,.18,.12);
  box(oak,-12.31,.18,0,.12,.18,16.91);
  for (let i=0;i<8;i++) {
    const x = -10.9+i*3.12;
    box(dark,x,1.48,-8.265,2.76,1.19,.073);
    const window=new T.MeshBasicMaterial({map:windowFinish(i)});
    mesh(new T.PlaneGeometry(2.55,.98),window,x,1.48,-8.181,1,1,1,scene,false);
    box(glass,x,1.48,-8.187,2.55,.98,.025,scene,false);
    box(dark,x,1.48,-8.166,.05,1.04,.045);
    box(ash,x,.92,-8.10,2.82,.11,.31);
  }
  for (let z=-6;z<8;z+=3) {
    box(dark,-12.29,1.34,z,.06,.85,2.48);
    box(pale,-12.251,1.34,z,.035,.66,2.29);
    box(dark,-12.22,1.34,z,.05,.76,.047);
  }

  function plant(x,z,scale=1, parent=null) {
    const stand = parent || group(x,0,z);
    const dx = parent ? x : 0, dz = parent ? z : 0;
    mesh(slim,cream,dx,.24*scale,dz,.30*scale,.49*scale,.30*scale,stand);
    round(ink,dx,.485*scale,dz,.277*scale,.03,.277*scale,stand);
    for (let i=0;i<9;i++) {
      const a=i*2.4;
      const radius = (.18+i%3*.055)*scale;
      const leaf=bulb(leaves[i%3],dx+Math.cos(a)*radius,(.68 + (i%4)*.12)*scale,
        dz+Math.sin(a)*radius,.33*scale,.09*scale,.12*scale,stand);
      leaf.rotation.y = -a;
      leaf.rotation.z = (i%3-1)*.53;
    }
  }

  function placard(text, x,z,w, color="#334439", background="#e9e4ce") {
    const paint = new T.MeshBasicMaterial({map:titleTexture(text,color,background)});
    const sign = mesh(new T.PlaneGeometry(w,w*.28125),paint,x,.011,z,1,1,1,scene,false);
    sign.rotation.x = -Math.PI/2;
    return sign;
  }

  function chair(x,z,angle=0,tone=slate) {
    const base=group(x,0,z);
    base.rotation.y=angle;
    round(dark,0,.08,0,.30,.06,.30,base);
    round(chrome,0,.29,0,.062,.40,.062,base);
    box(tone,0,.54,0,.64,.18,.58,base);
    box(tone,0,.88,.27,.59,.55,.15,base);
    for (const side of [-1,1]) box(dark,side*.335,.68,.055,.055,.055,.33,base);
  }

  function desk(x,z,index,role) {
    const base=group(x,0,z);
    const tint = material(ROLE_COLORS[index]);
    const zoneMat=index===0?deskRugs[0]:x<0?deskRugs[1]:deskRugs[2];
    box(zoneMat,0,.014,.32,2.74,.027,2.31,base,false);
    box(ash,0,.84,-.15,2.20,.15,1.20,base);
    for (const dx of [-.97,.97]) {
      box(dark,dx,.43,-.30,.071,.78,.075,base);
      box(dark,dx,.43,.32,.071,.78,.075,base);
      box(dark,dx,.125,0,.075,.065,.78,base);
    }
    box(oak,.62,.41,-.04,.44,.69,.64,base);
    box(brass,.62,.54,.291,.18,.035,.034,base);
    box(tint,0,1.17,-.70,2.13,.61,.099,base);
    box(dark,-.23,1.03,-.34,.33,.035,.18,base);
    box(dark,-.23,1.18,-.39,.08,.32,.08,base);
    box(dark,-.23,1.43,-.42,1.00,.62,.09,base);
    const screen = new T.MeshStandardMaterial({
      color:"#829b97",map:screenFinish(index),roughness:.50,emissive:"#87dbc8",emissiveIntensity:0
    });
    screen.emissiveMap = screen.map;
    box(screen,-.23,1.43,-.365,.92,.54,.024,base,false);
    if (index===5 || index===6 || index===7) {
      box(dark,.52,1.32,-.40,.45,.38,.075,base);
      box(screen,.52,1.32,-.352,.39,.31,.02,base,false);
    }
    box(dark,-.16,.935,.22,.52,.035,.17,base);
    bulb(cream,.24,.955,.2,.055,.032,.077,base);
    box(paper,-.78,.929,.21,.25,.014,.32,base);
    box(tint,-.78,.942,.20,.21,.015,.23,base);
    if (index===5 || index===7 || index===9) box(black,-.69,.946,-.30,.29,.025,.15,base);
    round(warm,.73,.982,.27,.075,.11,.075,base);
    round(ink,.73,1.04,.27,.056,.015,.056,base);
    round(dark,.81,.941,-.39,.15,.058,.15,base);
    box(brass,.82,1.20,-.40,.035,.47,.035,base);
    box(light,.77,1.43,-.37,.23,.035,.17,base,false);
    chair(x,z+.89,0,index%4===0?moss:slate);
    const identify=box(new T.MeshBasicMaterial({color:ROLE_COLORS[index]}),0,.031,1.50,1.28,.034,.075,base,false);
    identify.userData.role=role.name;
    const target=box(new T.MeshBasicMaterial({visible:false}),0,.85,.41,2.14,1.69,2.26,base,false);
    target.userData.role=role.name;
    return {screen,identify,target};
  }

  function roomWall(x,z,length,orientation) {
    const partition=group(x,0,z);
    partition.rotation.y=orientation;
    box(oak,0,.16,0,length,.26,.12,partition);
    box(glass,0,1.07,0,length,1.65,.049,partition,false);
    box(dark,0,1.91,0,length,.085,.098,partition);
    for (const dx of [-length/2,0,length/2]) box(dark,dx,1.03,0,.052,1.82,.092,partition);
  }
  box(tiles,0,.025,ROOM_Z,7.43,.068,6.36,scene,false);
  box(roomRug,0,.068,ROOM_Z,5.83,.022,4.49,scene,false);
  roomWall(0,ROOM_Z-3.1,7.46,0);
  roomWall(-3.68,ROOM_Z-.56,5.0,Math.PI/2);
  roomWall(3.68,ROOM_Z-.56,5.0,Math.PI/2);
  placard("WAR ROOM",0,3.05,2.0);
  const roomTable = group(0,0,ROOM_Z);
  round(dark,0,.44,0,1.09,.80,.60,roomTable);
  round(walnut,0,.89,0,2.14,.22,1.13,roomTable);
  round(oak,0,1.01,0,2.08,.035,1.09,roomTable);
  for (let i=0;i<8;i++) {
    const a=i*Math.PI/4;
    const x=Math.cos(a)*2.78, z=Math.sin(a)*1.79;
    chair(x,ROOM_Z+z,Math.atan2(x,z),moss);
    const sheet=box(i%2?paper:cream,x*.63,1.037,z*.56,.28,.021,.214,roomTable);
    sheet.rotation.y = i*.71;
  }
  const orbMesh = new T.IcosahedronGeometry(.34,1);
  const orb = mesh(orbMesh,new T.MeshStandardMaterial({
    color:"#8ddfc3",emissive:"#7be6b8",emissiveIntensity:.45,roughness:.26,metalness:.11
  }),0,1.88,ROOM_Z,1,1,1,scene,false);
  const orbFrame = new T.LineSegments(new T.EdgesGeometry(orbMesh),new T.LineBasicMaterial({
    color:"#d4fae2",transparent:true,opacity:.74
  }));
  orb.add(orbFrame);
  round(brass,0,1.05,ROOM_Z,.37,.065,.37);
  const ring = new T.Mesh(new T.TorusGeometry(.57,.018,8,50),new T.MeshBasicMaterial({color:"#8ddfc3"}));
  ring.position.set(0,1.85,ROOM_Z);
  ring.rotation.x = 1.01;
  scene.add(ring);

  // Lounge, shelving and studio props.
  box(rug,0,.014,6.58,6.53,.024,3.64,scene,false);
  function sofa(x,z,angle,tone) {
    const couch=group(x,0,z);
    couch.rotation.y=angle;
    box(dark,0,.17,0,2.40,.26,.91,couch);
    box(tone,0,.46,0,2.45,.40,.98,couch);
    box(tone,0,.78,-.38,2.47,.60,.23,couch);
    for (const dx of [-1.15,1.15]) box(tone,dx,.61,0,.21,.58,.99,couch);
    for (const dx of [-.62,0,.62]) box(cream,dx,.68,-.23,.46,.31,.23,couch);
  }
  sofa(-2.01,6.38,Math.PI/2,slate);
  sofa(2.01,6.38,-Math.PI/2,moss);
  round(oak,0,.36,6.40,.83,.12,.48);
  round(dark,0,.19,6.40,.36,.25,.26);
  box(paper,.15,.435,6.45,.32,.035,.23);
  round(warm,-.35,.46,6.36,.062,.11,.062);
  placard("LOUNGE",0,7.95,1.40);
  placard("RESEARCH", -8.35,4.53,2.17);
  placard("PRODUCTION",8.23,4.53,2.45);

  function cabinet(x,z,angle,width) {
    const cabinet = group(x,0,z);
    cabinet.rotation.y = angle;
    box(oak,0,.54,0,width,1.08,.56,cabinet);
    box(ash,0,1.10,0,width+.12,.10,.62,cabinet);
    for (let dx=-width/2+.3;dx<width/2;dx+=.64) {
      box(cream,dx,.58,.293,.54,.77,.05,cabinet);
      box(brass,dx,.73,.337,.19,.035,.041,cabinet);
    }
    return cabinet;
  }
  const bar=cabinet(8.30,7.56,0,4.35);
  box(dark,-1.31,1.40,0,.62,.48,.41,bar);
  box(chrome,-1.32,1.32,.22,.48,.13,.095,bar);
  round(cream,-1.29,1.20,.22,.063,.16,.063,bar);
  round(warm,1.13,1.30,.03,.19,.34,.19,bar);
  for (let i=0;i<4;i++) round(cream,-.64+i*.19,1.20,.13,.065,.13,.065,bar);
  const files=cabinet(-8.17,7.51,0,4.07);
  for(let i=0;i<13;i++) box(books[i%5],-1.56+i*.19,1.35,-.15,.13+(i%3)*.023,.38+(i%3)*.07,.31,files);
  const notes=group(-11.96,0,-3.0);
  notes.rotation.y=Math.PI/2;
  box(walnut,0,1.36,0,2.38,1.28,.12,notes);
  box(cream,0,1.36,.071,2.22,1.12,.03,notes);
  for (let i=0;i<8;i++) {
    const swatch=box(books[(i+1)%books.length],-.81+(i%4)*.52,1.07+Math.floor(i/4)*.46,.1,.34,.32,.016,notes);
    swatch.rotation.z=(i%3-1)*.10;
    box(ink,-.81+(i%4)*.52,1.07+Math.floor(i/4)*.46,.113,.16,.022,.012,notes);
  }
  for (const [x,z,s] of [[-11.86,-7.77,1.15],[11.6,-7.72,1.1],[-11.8,6.72,1.2],[11.7,6.5,1.16],[-4.26,6.94,.9],[4.27,6.94,.9],[-3.75,-6.65,.7],[3.65,-6.65,.7]]) plant(x,z,s);

  const characters = new Map();
  function worker(role,index) {
    const [x,z] = DESKS[index];
    const skin=material(["#d9ab80","#8d5b42","#cb8f6a","#b67759","#e7b890"][index%5]);
    const hair=material(["#302925","#312f29","#4b372b","#6c513c"][index%4]);
    const shirt=material(ROLE_COLORS[index], .81);
    const pos=new T.Vector3(x,0,z+.79);
    const root=group(pos.x,0,pos.z);
    root.rotation.y = Math.PI;
    const torso=bulb(shirt,0,.95,0,.265,.32,.19,root);
    const head=bulb(skin,0,1.40,0,.186,.221,.177,root);
    bulb(hair,0,1.493,-.036,.195,.147,.165,root);
    for (const side of [-1,1]) {
      bulb(skin,side*.175,1.41,0,.045,.065,.042,root);
      bulb(ink,side*.070,1.423,.163,.024,.021,.012,root);
      if (index===5 || index===6) bulb(ink,side*.188,1.424,-.015,.043,.083,.078,root);
    }
    const arms=[-1,1].map(side=>{
      const arm=bulb(shirt,side*.275,.91,.081,.100,.238,.097,root);
      const hand=bulb(skin,side*.263,.779,.173,.07,.075,.073,root);
      return [arm,hand];
    });
    const legs=[-1,1].map(side=>{
      const leg=bulb(dark,side*.115,.465,.071,.101,.258,.109,root);
      const shoe=bulb(ink,side*.118,.208,.111,.106,.084,.159,root);
      return [leg,shoe];
    });
    const halo = round(new T.MeshBasicMaterial({color:"#79edaa",transparent:true,opacity:.65}),
      0,.024,0,.48,.026,.45,root,false);
    const marker=bulb(new T.MeshBasicMaterial({color:"#8fffc2"}),0,1.84,0,.086,.086,.086,root,false);
    marker.visible=false;
    halo.visible=false;
    const hit=box(new T.MeshBasicMaterial({visible:false}),0,.91,0,.72,1.8,.72,root,false);
    hit.userData.role=role.name;
    const workstation=desk(x,z,index,role);
    const label=document.createElement("div");
    label.className="scene-label";
    label.textContent=role.name;
    label.hidden=true;
    labels.append(label);
    characters.set(role.name,{root,head,torso,arms,legs,home:pos,halo,marker,hit,workstation,label,
      labelWidth:role.name.length*5.5+15,status:"idle",target:pos.clone(), route:[], meeting:false, selected:false});
  }
  roles.forEach(worker);

  const ray = new T.Raycaster();
  const pointer = new T.Vector2();
  let down;
  renderer.domElement.addEventListener("pointerdown", e => { down=[e.clientX,e.clientY]; });
  renderer.domElement.addEventListener("pointerup", e => {
    if (!down || Math.hypot(e.clientX-down[0],e.clientY-down[1])>7) return;
    const rect=renderer.domElement.getBoundingClientRect();
    pointer.set((e.clientX-rect.left)/rect.width*2-1, -(e.clientY-rect.top)/rect.height*2+1);
    ray.setFromCamera(pointer,camera);
    const hits=ray.intersectObjects([...characters.values()].flatMap(c=>[c.hit,c.workstation.target]),false);
    if (hits.length) onPick(hits[0].object.userData.role);
  });

  function fit() {
    if (!host.clientWidth || !host.clientHeight) return;
    const aspect=host.clientWidth/host.clientHeight;
    const vertical=Math.max(10.7,(aspect<1.15?15.7:14.8)/aspect);
    const horizontal=vertical*aspect;
    Object.assign(camera,{left:-horizontal,right:horizontal,top:vertical,bottom:-vertical});
    camera.updateProjectionMatrix();
    renderer.setSize(host.clientWidth,host.clientHeight,false);
  }
  let focusView;
  function reset() {
    focusView=null;
    camera.position.set(18.3,23.8,26.9);
    camera.zoom=1;
    camera.up.copy(UP);
    controls.target.copy(CENTER);
    camera.updateProjectionMatrix();
    controls.update();
  }
  new ResizeObserver(fit).observe(host);
  reset();
  fit();
  const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const cords = new Map();
  const clockStart = performance.now();
  let prev=clockStart;

  function waypoint(character,x,z) {
    character.route.push(new T.Vector3(x,0,z));
  }

  function routeTo(character,destination,meeting) {
    character.route=[];
    const pos=character.root.position;
    if (pos.distanceTo(destination)<.05) {
      character.target.copy(destination);
      return;
    }
    if (meeting) {
      const side=Math.sign(character.home.x || 1);
      if (Math.abs(pos.x)>4) {
        waypoint(character,pos.x,pos.z+.44);
        const aisle=Math.abs(character.home.x)>8?side*11.45:side*4.33;
        waypoint(character,aisle,pos.z+.44);
        waypoint(character,aisle,3.14);
      } else if (pos.z<-3.4) {
        const aisle=side*4.33;
        waypoint(character,aisle,pos.z);
        waypoint(character,aisle,3.14);
      }
      const insideSide=Math.sign(destination.x || side);
      waypoint(character,insideSide*3.07,3.10);
      if (destination.z<ROOM_Z-.55) {
        waypoint(character,insideSide*3.07,ROOM_Z-2.40);
        waypoint(character,destination.x,ROOM_Z-2.40);
      }
    } else if (Math.abs(pos.x)<3.72 && pos.z<2.4 && pos.z>-3.8) {
      const side=Math.sign(character.home.x || 1);
      waypoint(character,Math.sign(pos.x || side)*3.05,3.14);
      const aisle=(Math.abs(character.home.x)>8?11.45:4.33)*side;
      waypoint(character,aisle,3.14);
      waypoint(character,aisle,character.home.z+.44);
      waypoint(character,character.home.x,character.home.z+.44);
    }
    character.route.push(destination);
    character.target.copy(destination);
    if (reduced) {
      character.root.position.copy(destination);
      character.route=[];
    }
  }

  let isMeeting=false;
  function setState(states, group, selected) {
    const available=Array.from({length:8},(_,seat)=>{
      const angle=seat*Math.PI/4;
      return new T.Vector3(Math.cos(angle)*2.78,0,ROOM_Z+Math.sin(angle)*1.79);
    });
    const seats=new Map();
    for (const name of group.slice(0,8)) {
      const home=characters.get(name)?.home;
      if (!home) continue;
      available.sort((a,b)=>a.distanceToSquared(home)-b.distanceToSquared(home));
      seats.set(name,available.shift());
    }
    isMeeting = seats.size>1;
    for (const [name, c] of characters) {
      const status=states[name]?.status || "idle";
      const seat=seats.get(name);
      const destination=seat || c.home;
      if (c.target.distanceTo(destination)>.05) routeTo(c,destination,Boolean(seat));
      c.meeting=Boolean(seat);
      c.status=status;
      c.selected=selected===name;
      c.workstation.screen.emissiveIntensity=status==="working"?.69:0;
      c.halo.visible=c.selected || status==="working";
      c.halo.material.color.set(c.selected?"#eec77c":"#80ddab");
      c.marker.visible=status==="working" || status==="blocked" || status==="review";
      c.marker.material.color.set(status==="working"?"#94fac0":status==="review"?"#f4cf77":"#f4a391");
      c.label.hidden=!c.selected && status!=="working";
      c.label.classList.toggle("selected",c.selected);
      if (!seat && cords.has(name)) {
        const line=cords.get(name);
        scene.remove(line);
        line.geometry.dispose();
        line.material.dispose();
        cords.delete(name);
      } else if (seat && !cords.has(name)) {
        const points=new Float32Array(9);
        const geometry=new T.BufferGeometry();
        geometry.setAttribute("position",new T.BufferAttribute(points,3));
        const line=new T.Line(geometry,new T.LineBasicMaterial({color:"#8cefbd",opacity:.60,transparent:true}));
        line.frustumCulled=false;
        scene.add(line);
        cords.set(name,line);
      }
    }
  }

  function frame(now) {
    const time=(now-clockStart)/1000;
    const dt=Math.min((now-prev)/1000,.095);
    prev=now;
    if (focusView) {
      const factor=reduced?1:1-Math.exp(-dt*8);
      DETAIL.copy(focusView.target).sub(controls.target).multiplyScalar(factor);
      controls.target.add(DETAIL);
      camera.position.add(DETAIL);
      camera.zoom=T.MathUtils.lerp(camera.zoom,focusView.zoom,factor);
      camera.updateProjectionMatrix();
      if (controls.target.distanceToSquared(focusView.target)<.0002 && Math.abs(camera.zoom-focusView.zoom)<.004) focusView=null;
    }
    controls.update();
    orb.position.y=1.88+(reduced?0:Math.sin(time*1.5)*.07);
    orb.rotation.y=reduced?0:time*.35;
    orb.material.emissiveIntensity=isMeeting?.82+(reduced?0:Math.sin(time*3.2)*.24):.25;
    ring.rotation.z=reduced?0:time*.2;
    const width=host.clientWidth, height=host.clientHeight;
    const visibleLabels=[];
    for (const [name,c] of characters) {
      const position=c.root.position;
      const next=c.route[0];
      if (next) {
        DETAIL.subVectors(next,position);
        const length=DETAIL.length();
        if (length<.06) c.route.shift();
        else {
          position.addScaledVector(DETAIL,Math.min(1,dt*4.05/length));
          c.root.rotation.y=Math.atan2(DETAIL.x,DETAIL.z);
        }
      }
      const walking=c.route.length>0;
      if (!walking) c.root.rotation.y=c.meeting ? Math.atan2(-position.x,ROOM_Z-position.z) : Math.PI;
      const typing=c.status==="working"&&!walking&&!reduced;
      const wave=typing?Math.sin(time*19)*.035:0;
      c.torso.position.y=walking?1.04:.94;
      c.head.position.y=walking?1.41+Math.sin(time*15)*.021:1.40;
      for (const [i,[arm,hand]] of c.arms.entries()) {
        arm.rotation.x=walking?Math.sin(time*12+i*Math.PI)*.43:-.65;
        hand.position.y=.78+(i?wave:-wave);
        hand.position.z=walking?.10:.29;
      }
      for (const [i,[leg,shoe]] of c.legs.entries()) {
        const stride=walking?Math.sin(time*12+i*Math.PI):0;
        leg.rotation.x=walking?stride*.68:-.48;
        shoe.position.z=.12+stride*.22;
      }
      const line=cords.get(name);
      if (line) {
        const points=line.geometry.attributes.position;
        points.setXYZ(0,0,orb.position.y,ROOM_Z);
        points.setXYZ(1,position.x*.43,1.86+(reduced?0:Math.sin(time*3.1)*.16),T.MathUtils.lerp(ROOM_Z,position.z,.43));
        points.setXYZ(2,position.x,1.45,position.z);
        points.needsUpdate=true;
        line.visible=!walking;
      }
      if (!c.label.hidden) {
        PROJECTED.set(position.x,2.08,position.z).project(camera);
        visibleLabels.push({c,x:(PROJECTED.x*.5+.5)*width,y:(.5-PROJECTED.y*.5)*height});
      }
    }
    const placed=[];
    visibleLabels.sort((a,b)=>Number(b.c.selected)-Number(a.c.selected) || a.y-b.y);
    for (const {c,x,y} of visibleLabels) {
      const half=c.labelWidth*.5;
      let top=y;
      while (placed.some(p=>Math.abs(p.x-x)<p.half+half+4 && Math.abs(p.top-top)<19)) top-=20;
      const inside=top>=51 && y<=height-38 && x>=half+4 && x<=width-half-4;
      c.label.style.visibility=inside?"":"hidden";
      if (inside) {
        c.label.style.left=`${x}px`;
        c.label.style.top=`${top}px`;
        placed.push({x,top,half});
      }
    }
    renderer.render(scene,camera);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  controls.addEventListener("start",()=>{focusView=null;});
  return {setState,reset,focus(name) {
    const [x,y,z,zoom]=VIEWS[name];
    focusView={target:new T.Vector3(x,y,z),zoom};
  },zoom(amount) {
    focusView=null;
    camera.zoom=T.MathUtils.clamp(camera.zoom*amount,controls.minZoom,controls.maxZoom);
    camera.updateProjectionMatrix();
  }};
}
