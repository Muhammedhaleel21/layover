import "./globals.css";import type {Metadata,Viewport} from "next";
export const metadata:Metadata={title:"LAYOVER – Explore the Unknown. Beat the Clock.",description:"Turn spare travel time into a real-world mystery adventure."};
export const viewport:Viewport={width:"device-width",initialScale:1};
export default function R({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
