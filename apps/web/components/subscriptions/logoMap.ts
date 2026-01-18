
function normalizeForMatch(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "")
}

const LOGO_MAP: Record<string, string> = {
  netflix: "/logos/netflix_logo.png",
  spotify: "/logos/spotify_logo.png",
  discord: "/logos/discord_logo.png",
  
  adobe: "/logos/adobe_logo.png",
  adobecreativecloud: "/logos/adobe_logo.png",
  adobecc: "/logos/adobe_logo.png",
  
  claude: "/logos/claude_logo.png",
  claudeai: "/logos/claude_logo.png",
  anthropic: "/logos/claude_logo.png",
  
  apple: "/logos/apple_logo.png",
  applemusic: "/logos/apple_logo.png",
  appletv: "/logos/apple_logo.png",
  appletvplus: "/logos/apple_logo.png",
  appleicloud: "/logos/apple_logo.png",
  icloud: "/logos/apple_logo.png",
  appleone: "/logos/apple_logo.png",
  applenews: "/logos/apple_logo.png",
  applearcade: "/logos/apple_logo.png",
  applefitness: "/logos/apple_logo.png",
  
}


export function getLogoForSubscription(name: string): string | undefined {
  const normalized = normalizeForMatch(name)
  
  if (LOGO_MAP[normalized]) {
    return LOGO_MAP[normalized]
  }
  
  for (const [key, logo] of Object.entries(LOGO_MAP)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      return logo
    }
  }
  
  return undefined
}

export function getInitials(name: string): string {
  const words = name.trim().split(/\s+/)
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}
