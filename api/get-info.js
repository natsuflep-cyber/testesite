const ytdl = require('ytdl-core');

module.exports = async (req, res) => {
  // Habilita CORS para permitir que o frontend chame a API
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { url } = req.query;

  if (!url) {
    return res.status(400).json({ error: 'URL não fornecida' });
  }

  try {
    // Verifica se é um link válido do YouTube
    if (!ytdl.validateURL(url)) {
      return res.status(400).json({ error: 'URL inválida do YouTube' });
    }

    const info = await ytdl.getInfo(url);
    
    // Filtra formatos: prioriza mp4 com áudio e vídeo juntos
    const formats = ytdl.filterFormats(info.formats, 'videoandaudio')
      .filter(f => f.container === 'mp4')
      .sort((a, b) => b.height - a.height)
      .slice(0, 5); // Pega os 5 melhores

    // Adiciona opção de áudio puro
    const audioOnly = ytdl.filterFormats(info.formats, 'audioonly')
      .sort((a, b) => b.bitrate - a.bitrate)[0];

    const resultFormats = formats.map(f => ({
      label: `Vídeo ${f.height}p`,
      url: f.url,
      ext: 'mp4',
      size: f.contentLength ? `${(f.contentLength / 1024 / 1024).toFixed(1)} MB` : 'N/A'
    }));

    if (audioOnly) {
      resultFormats.push({
        label: 'Áudio Apenas',
        url: audioOnly.url,
        ext: audioOnly.container === 'webm' ? 'webm' : 'm4a',
        size: audioOnly.contentLength ? `${(audioOnly.contentLength / 1024 / 1024).toFixed(1)} MB` : 'N/A'
      });
    }

    return res.status(200).json({
      title: info.videoDetails.title,
      formats: resultFormats
    });

  } catch (error) {
    console.error('Erro no ytdl:', error.message);
    // Retorna JSON de erro em vez de quebrar o servidor
    return res.status(500).json({ 
      error: 'Falha ao processar vídeo. O YouTube pode ter bloqueado este IP ou o vídeo pode ser privado.' 
    });
  }
};
