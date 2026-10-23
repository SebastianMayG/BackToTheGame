import { onBeforeUnmount, watch } from 'vue'
import type { CommentaryLine, Level } from '@/api/types'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'

// Voice commentary. Azure AI Speech (POST /api/voice) reads every line with the narrator's neural voice
// and turns the line's emotion into prosody. If the server has no Speech or it fails, the browser's
// speech synthesis takes over, so the commentary is never silent.

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
  const supported = typeof window !== 'undefined' && ('speechSynthesis' in window || 'Audio' in window)
  let queue: CommentaryLine[] = []
  let speaking = false
  let azureDown = false // after one failure stay on the browser voice for the rest of the session
  let audio: HTMLAudioElement | null = null
  let generation = 0 // bumped by cancel() so late results of an old line are ignored

  /** Play one line with Azure AI Speech. Returns false when it could not, so the caller falls back. */
  async function speakAzure(line: CommentaryLine): Promise<boolean> {
    try {
      const res = await fetch('/api/voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: clean(line.text), speaker: 'narrator', lang: line.lang, emotion: line.emotion }),
      })
      if (!res.ok) return false
      const url = URL.createObjectURL(await res.blob())
      await new Promise<void>((resolve, reject) => {
        const a = new Audio(url)
        audio = a
        a.onended = () => resolve()
        a.onerror = () => reject(new Error('audio'))
        a.play().catch(reject)
      })
      URL.revokeObjectURL(url)
      return true
    } catch {
      return false
    } finally {
      audio = null
    }
  }

  function speakBrowser(line: CommentaryLine): Promise<void> {
    return new Promise((resolve) => {
      if (!('speechSynthesis' in window)) return resolve()
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

  async function speak(line: CommentaryLine, gen: number): Promise<void> {
    if (!azureDown) {
      if (await speakAzure(line)) return
      if (gen !== generation) return // cancelled while loading: not an Azure failure
      azureDown = true
    }
    await speakBrowser(line)
  }

  async function pump() {
    if (speaking || !queue.length) return
    speaking = true
    const gen = generation
    const line = queue.shift()!
    await speak(line, gen)
    if (gen !== generation) return // cancel() already reset the state
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
    if (line.lang !== profile.lang) return
    // one voice: it reads the big moments and every line the AI narrator wrote
    if (line.level > threshold() && line.source !== 'ai') return
    enqueue(line)
  })

  function threshold(): Level {
    return profile.mode === 'accessible' ? 2 : 1
  }

  function cancel() {
    generation++
    queue = []
    audio?.pause()
    audio = null
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
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
