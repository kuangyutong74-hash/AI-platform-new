import { useCallback, useRef, useState } from 'react';

/**
 * Browser Speech-to-Text hook using the Web Speech API.
 * Works in Chrome/Edge. Shows interim results for live feedback.
 */
export function useSpeechInput() {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const recognitionRef = useRef<any>(null);

  const startListening = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        reject(new Error('请用 Chrome 浏览器打开才能语音输入'));
        return;
      }

      // Clean up previous instance
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch {}
      }

      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.lang = 'zh-CN';
      recognition.interimResults = true;   // Show live feedback
      recognition.maxAlternatives = 1;
      recognition.continuous = false;      // Auto-stop after one utterance

      let finalTranscript = '';
      let resolved = false;
      let startTimer: ReturnType<typeof setTimeout> | null = null;
      let sessionTimer: ReturnType<typeof setTimeout> | null = null;

      const clearTimers = () => {
        if (startTimer) clearTimeout(startTimer);
        if (sessionTimer) clearTimeout(sessionTimer);
        startTimer = null;
        sessionTimer = null;
      };

      const finish = (error?: Error) => {
        if (resolved) return;
        resolved = true;
        clearTimers();
        recognitionRef.current = null;
        setListening(false);
        setInterim('');
        if (error) reject(error);
        else resolve(finalTranscript.trim());
      };

      recognition.onstart = () => {
        if (startTimer) clearTimeout(startTimer);
        startTimer = null;
        setListening(true);
        setInterim('');
        sessionTimer = setTimeout(() => {
          try { recognition.stop(); } catch {}
        }, 15_000);
      };

      recognition.onresult = (e: any) => {
        let interimTranscript = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const result = e.results[i];
          if (result.isFinal) {
            finalTranscript += result[0].transcript;
          } else {
            interimTranscript += result[0].transcript;
          }
        }
        setInterim(interimTranscript);

        // If continuous=false, the first final result means we're done
        if (finalTranscript && !resolved) {
          finish();
        }
      };

      recognition.onend = () => {
        if (finalTranscript.trim()) finish();
        else finish(new Error('没有听到声音，请靠近麦克风后再试一次~'));
      };

      recognition.onerror = (e: any) => {
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
          finish(new Error('麦克风权限未开启，请在地址栏左侧允许后重试~'));
        } else if (e.error === 'aborted') {
          finish(new Error('已停止语音输入'));
        } else if (e.error === 'no-speech') {
          finish(new Error('没有听到声音，请靠近麦克风后再试一次~'));
        } else if (e.error === 'network') {
          finish(new Error('语音识别服务连接失败，请检查网络或直接打字~'));
        } else {
          finish(new Error('语音识别出错，请再试一次~'));
        }
      };

      try {
        recognition.start();
        startTimer = setTimeout(() => {
          try { recognition.abort(); } catch {}
          finish(new Error('麦克风启动超时，请检查浏览器麦克风权限~'));
        }, 5_000);
      } catch {
        finish(new Error('麦克风启动失败，请刷新页面后重试~'));
      }
    });
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }
    setListening(false);
    setInterim('');
  }, []);

  return { startListening, stopListening, listening, interim };
}
