import { onBeforeUnmount, watch } from 'vue'
import type { CommentaryLine, Level } from '@/api/types'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'

// Voice commentary. For now it uses the browser's speech synthesis; the Azure AI Speech
// backend (/api/voice, two neural voices with SSML emotion) will plug in behind `speak()`.

const LOCALES = { es: ['es-MX', 'es-ES', 'es-US', 'es'], en: ['en-GB', 'en-US', 'en'] } as const
const MAX_QUEUE = 3

function pickVoices(lang: 'es' | 'en'): SpeechSynthesisVoice[] {
  const all = window.speechSynthesis.getVoices()
  for (const loc of LOCALES[lang]) {
    const found = all.filter((v) => v.lang.toLowerCase().startsWith(loc.toLowerCase()))
    if (found.length) return found
  }
  return []
}

const clean = (text: string) => text.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '').trim()

export function useVoice() {
  const profile = useProfile()
  const match = useMatch()
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  let queue: CommentaryLine[] = []
  let speaking = false

  const threshold = (): Level => (profile.mode === 'accessible' ? 2 : 1)

  function speak(line: CommentaryLine): Promise<void> {
    return new Promise((resolve) => {
      const u = new SpeechSynthesisUtterance(clean(line.text))
      const voices = pickVoices(line.lang)
      // narrator and pundit get different voices when the browser offers more than one
      const voice = line.speaker === 'pundit' ? (voices[1] ?? voices[0]) : voices[0]
      if (voice) u.voice = voice
      u.lang = voice?.lang ?? (line.lang === 'es' ? 'es-MX' : 'en-GB')
      u.rate = line.emotion === 'excited' ? 1.15 : line.speaker === 'pundit' ? 0.98 : 1.05
      u.pitch = line.emotion === 'excited' ? 1.2 : line.emotion === 'disappointed' ? 0.85 : line.speaker === 'pundit' ? 0.9 : 1
      u.onend = () => resolve()
      u.onerror = () => resolve()
      window.speechSynthesis.speak(u)
    })
  }

  async function pump() {
    if (speaking || !queue.length) return
    speaking = true
    const line = queue.shift()!
    await speak(line)
    speaking = false
    void pump()
  }

  function enqueue(line: CommentaryLine) {
    // stay live: when the voice falls behind, drop everything but the biggest moments
    if (queue.length >= MAX_QUEUE) queue = queue.filter((l) => l.level === 1).slice(-MAX_QUEUE + 1)
    queue.push(line)
    void pump()
  }

  const off = match.onLine((line) => {
    if (!supported || !profile.voice) return
    if (line.lang !== profile.lang || line.level > threshold()) return
    enqueue(line)
  })

  function cancel() {
    queue = []
    if (supported) window.speechSynthesis.cancel()
    speaking = false
  }

  watch(
    () => profile.voice,
    (on) => {
      if (!on) cancel()
    },
  )
  onBeforeUnmount(() => {
    off()
    cancel()
  })

  return { supported, cancel }
}
