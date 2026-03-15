import { useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { Box, Paper, Typography } from '@mui/material'
import HelpTooltip from '../common/HelpTooltip'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { ScanResults } from '../../types'

// Fix default marker icon in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface GeoMapProps {
  scanResults: ScanResults
}

const GeoMap = ({ scanResults }: GeoMapProps) => {
  const markers = useMemo(() => {
    const geo = scanResults.geoip_info || {}
    return Object.entries(geo)
      .filter(([, v]) => v?.latitude != null && v?.longitude != null)
      .map(([ip, info]) => ({
        ip,
        lat: info!.latitude!,
        lng: info!.longitude!,
        city: info!.city,
        country: info!.country,
      }))
  }, [scanResults.geoip_info])

  if (markers.length === 0) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Typography variant="h6">Geolocation</Typography>
          <HelpTooltip topic="geo_map" />
        </Box>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            No geolocation data available. Add GeoLite2-City.mmdb to the backend and rescan.
          </Typography>
        </Paper>
      </Box>
    )
  }

  const center: [number, number] =
    markers.length === 1
      ? [markers[0].lat, markers[0].lng]
      : [
          markers.reduce((s, m) => s + m.lat, 0) / markers.length,
          markers.reduce((s, m) => s + m.lng, 0) / markers.length,
        ]

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="h6">Geolocation</Typography>
        <HelpTooltip topic="geo_map" />
      </Box>
      <Paper sx={{ overflow: 'hidden', borderRadius: 2 }}>
        <MapContainer
        center={center}
        zoom={markers.length === 1 ? 8 : 3}
        style={{ height: 400, width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {markers.map((m) => (
          <Marker key={m.ip} position={[m.lat, m.lng]}>
            <Popup>
              <strong>{m.ip}</strong>
              <br />
              {[m.city, m.country].filter(Boolean).join(', ')}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Paper>
    </Box>
  )
}

export default GeoMap
