const NCALAYER_URL = 'wss://127.0.0.1:13579/'

function parseNcaLayerMessage(raw) {
  const data = typeof raw === 'string' ? JSON.parse(raw) : raw
  if (data.status === false) {
    throw new Error(data.message || 'NCALayer отклонил подпись.')
  }
  if (data.code && String(data.code) !== '200') {
    throw new Error(data.message || 'NCALayer вернул ошибку.')
  }
  if (typeof data.body === 'string' && data.body) {
    return data.body
  }
  if (typeof data.responseObject === 'string' && data.responseObject) {
    return data.responseObject
  }
  if (typeof data.result === 'string' && data.result) {
    return data.result
  }
  if (data.result && typeof data.result.cms === 'string') {
    return data.result.cms
  }
  throw new Error('NCALayer не вернул CMS-подпись.')
}

function sendSignRequest(socket, challenge) {
  socket.send(JSON.stringify({
    module: 'kz.gov.pki.knca.basics',
    method: 'sign',
    args: {
      format: 'cms',
      data: btoa(challenge),
      signingParams: {
        decode: true,
        encapsulate: true,
        detached: false,
      },
      locale: 'ru',
    },
  }))
}

function sendLegacySignRequest(socket, challenge) {
  socket.send(JSON.stringify({
    module: 'kz.gov.pki.knca.commonUtils',
    method: 'createCMSSignatureFromBase64',
    args: ['PKCS12', 'SIGNATURE', btoa(challenge), true],
  }))
}

export function signChallengeWithNcaLayer(challenge) {
  return new Promise((resolve, reject) => {
    let settled = false
    let usedLegacy = false
    const socket = new WebSocket(NCALAYER_URL)
    const timer = window.setTimeout(() => {
      socket.close()
      fail(new Error('NCALayer не отвечает. Запустите NCALayer и повторите подпись.'))
    }, 25000)

    function fail(error) {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      reject(error)
    }

    function succeed(cms) {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      socket.close()
      resolve(cms)
    }

    socket.addEventListener('error', () => {
      fail(new Error('Не удалось подключиться к NCALayer. Убедитесь, что приложение запущено на этом компьютере.'))
    })

    socket.addEventListener('open', () => {
      sendSignRequest(socket, challenge)
    })

    socket.addEventListener('message', (event) => {
      try {
        const cms = parseNcaLayerMessage(event.data)
        succeed(cms)
      } catch (error) {
        if (!usedLegacy) {
          usedLegacy = true
          sendLegacySignRequest(socket, challenge)
          return
        }
        fail(error)
      }
    })
  })
}

export function buildDevCms(challenge, extra = {}) {
  const payload = {
    challenge,
    iin: extra.iin || '880420301999',
    full_name: extra.full_name || 'ИВАНОВ ИВАН ИВАНОВИЧ',
    birth_date: extra.birth_date || '1988-04-20',
    certificate_type: 'individual',
    serial_number: 'dev-test',
    issuer: 'DEV NCA',
    valid_from: new Date().toISOString(),
    valid_to: new Date(Date.now() + 86400000 * 365).toISOString(),
  }
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload))))
}

export function isDevEcpEnabled() {
  return import.meta.env.VITE_ECP_ALLOW_DEV === 'true'
}
