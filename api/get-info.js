const ytdl = require('ytdl-core');

exports.config = {
  maxDuration: 30, // segundos
};

exports.handler = async (req, res) => {
  // Configurar CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { url } = req.query;

  if (!url) {
    return res.status(400).json({ error: 'URL não fornecida' });
  }

  try {
    const info = await ytdl.getInfo(url);
    const formats = ytdl.filterFormats(info.formats, 'videoandaudio');
    
    // Filtrar e organizar as melhores opções
    const qualities = formats
      .filter(f => f.container === 'mp4') // Apenas MP4 para compatibilidade
      .sort((a, b) => b.height - a.height) // Ordenar por resolução (maior primeiro)
      .slice(0, 5) // Pegar as 5 melhores qualidades
      .map(f => ({
        label: `${f.height}p`,
        url: f.url, // Link direto de download
        ext: 'mp4',
        size: f.contentLength ? (f.contentLength / 1024 / 1024).toFixed(2) + ' MB' : 'Tamanho desconhecido'
      }));

    // Opção de áudio apenas
    const audioFormat = ytdl.filterFormats(info.formats, 'audioonly').sort((a, b) => b.bitrate - a.bitrate)[0];
    if (audioFormat) {
      qualities.push({
        label: 'Áudio Apenas (MP3/M4A)',
        url: audioFormat.url,
        ext: audioFormat.container === 'webm' ? 'webm' : 'm4a',
        size: audioFormat.contentLength ? (audioFormat.contentLength / 1024 / 1024).toFixed(2) + ' MB' : 'Tamanho desconhecido'
      });
    }

    return res.status(200).json({
      title: info.videoDetails.title,
      thumbnail: info.videoDetails.thumbnails[0].url,
      formats: qualities
    });

  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: 'Erro ao processar vídeo. O link pode ser inválido ou estar bloqueado.' });
  }
};
