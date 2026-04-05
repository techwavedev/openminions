"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const react_1 = __importStar(require("react"));
const client_1 = require("react-dom/client");
const react_2 = require("@xyflow/react");
require("@xyflow/react/dist/style.css");
const initialNodes = [
    { id: '1', position: { x: 100, y: 100 }, data: { label: 'Architect Agent' } },
    { id: '2', position: { x: 400, y: 100 }, data: { label: 'Reporter Agent' } },
];
const initialEdges = [{ id: 'e1-2', source: '1', target: '2' }];
function BuilderApp() {
    const [nodes, setNodes, onNodesChange] = (0, react_2.useNodesState)(initialNodes);
    const [edges, setEdges, onEdgesChange] = (0, react_2.useEdgesState)(initialEdges);
    const onConnect = (0, react_1.useCallback)((params) => setEdges((eds) => (0, react_2.addEdge)(params, eds)), [setEdges]);
    return (react_1.default.createElement("div", { style: { width: '100vw', height: '100vh', background: 'transparent' } },
        react_1.default.createElement(react_2.ReactFlow, { nodes: nodes, edges: edges, onNodesChange: onNodesChange, onEdgesChange: onEdgesChange, onConnect: onConnect, fitView: true },
            react_1.default.createElement(react_2.Background, null))));
}
const rootElement = document.getElementById('root');
if (rootElement) {
    const root = (0, client_1.createRoot)(rootElement);
    root.render(react_1.default.createElement(BuilderApp, null));
}
//# sourceMappingURL=BuilderApp.js.map