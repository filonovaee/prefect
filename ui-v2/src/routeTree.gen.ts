/* eslint-disable */

// @ts-nocheck

// noinspection JSUnusedGlobalSymbols

// This file was automatically generated by TanStack Router.
// You should NOT make any changes in this file as it will be overwritten.
// Additionally, you should also exclude this file from your linter and/or formatter to prevent it from being checked or modified.

// Import Routes

import { Route as rootRoute } from "./routes/__root";
import { Route as SettingsImport } from "./routes/settings";
import { Route as FlowsIndexImport } from "./routes/flows/index";
import { Route as FlowsFlowIdImport } from "./routes/flows/flow.$id";

// Create/Update Routes

const SettingsRoute = SettingsImport.update({
	id: "/settings",
	path: "/settings",
	getParentRoute: () => rootRoute,
} as any);

const FlowsIndexRoute = FlowsIndexImport.update({
	id: "/flows/",
	path: "/flows/",
	getParentRoute: () => rootRoute,
} as any);

const FlowsFlowIdRoute = FlowsFlowIdImport.update({
	id: "/flows/flow/$id",
	path: "/flows/flow/$id",
	getParentRoute: () => rootRoute,
} as any);

// Populate the FileRoutesByPath interface

declare module "@tanstack/react-router" {
	interface FileRoutesByPath {
		"/settings": {
			id: "/settings";
			path: "/settings";
			fullPath: "/settings";
			preLoaderRoute: typeof SettingsImport;
			parentRoute: typeof rootRoute;
		};
		"/flows/": {
			id: "/flows/";
			path: "/flows";
			fullPath: "/flows";
			preLoaderRoute: typeof FlowsIndexImport;
			parentRoute: typeof rootRoute;
		};
		"/flows/flow/$id": {
			id: "/flows/flow/$id";
			path: "/flows/flow/$id";
			fullPath: "/flows/flow/$id";
			preLoaderRoute: typeof FlowsFlowIdImport;
			parentRoute: typeof rootRoute;
		};
	}
}

// Create and export the route tree

export interface FileRoutesByFullPath {
	"/settings": typeof SettingsRoute;
	"/flows": typeof FlowsIndexRoute;
	"/flows/flow/$id": typeof FlowsFlowIdRoute;
}

export interface FileRoutesByTo {
	"/settings": typeof SettingsRoute;
	"/flows": typeof FlowsIndexRoute;
	"/flows/flow/$id": typeof FlowsFlowIdRoute;
}

export interface FileRoutesById {
	__root__: typeof rootRoute;
	"/settings": typeof SettingsRoute;
	"/flows/": typeof FlowsIndexRoute;
	"/flows/flow/$id": typeof FlowsFlowIdRoute;
}

export interface FileRouteTypes {
	fileRoutesByFullPath: FileRoutesByFullPath;
	fullPaths: "/settings" | "/flows" | "/flows/flow/$id";
	fileRoutesByTo: FileRoutesByTo;
	to: "/settings" | "/flows" | "/flows/flow/$id";
	id: "__root__" | "/settings" | "/flows/" | "/flows/flow/$id";
	fileRoutesById: FileRoutesById;
}

export interface RootRouteChildren {
	SettingsRoute: typeof SettingsRoute;
	FlowsIndexRoute: typeof FlowsIndexRoute;
	FlowsFlowIdRoute: typeof FlowsFlowIdRoute;
}

const rootRouteChildren: RootRouteChildren = {
	SettingsRoute: SettingsRoute,
	FlowsIndexRoute: FlowsIndexRoute,
	FlowsFlowIdRoute: FlowsFlowIdRoute,
};

export const routeTree = rootRoute
	._addFileChildren(rootRouteChildren)
	._addFileTypes<FileRouteTypes>();

/* ROUTE_MANIFEST_START
{
  "routes": {
    "__root__": {
      "filePath": "__root.tsx",
      "children": [
        "/settings",
        "/flows/",
        "/flows/flow/$id"
      ]
    },
    "/settings": {
      "filePath": "settings.tsx"
    },
    "/flows/": {
      "filePath": "flows/index.tsx"
    },
    "/flows/flow/$id": {
      "filePath": "flows/flow.$id.tsx"
    }
  }
}
ROUTE_MANIFEST_END */
