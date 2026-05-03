import { IconButton, Popover, Typography, Box } from '@mui/material'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { HelpTopicId } from '../../i18n/locales/helpTopics.en'

export interface HelpContent {
  title: string
  what: string
  whyImportant: string
  whyBad?: string
  tips?: string
}

interface HelpTooltipProps {
  topic: HelpTopicId
  size?: 'small' | 'medium'
}

const HelpTooltip = ({ topic, size = 'small' }: HelpTooltipProps) => {
  const { t } = useTranslation()
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const topicBase = `help.topics.${topic}` as const

  const content: HelpContent = {
    title: t(`${topicBase}.title`),
    what: t(`${topicBase}.what`),
    whyImportant: t(`${topicBase}.whyImportant`),
    whyBad: t(`${topicBase}.whyBad`, { defaultValue: '' }) || undefined,
    tips: t(`${topicBase}.tips`, { defaultValue: '' }) || undefined,
  }

  const handleClick = (e: React.MouseEvent<HTMLElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setAnchorEl(e.currentTarget)
  }

  const handleClose = () => setAnchorEl(null)
  const open = Boolean(anchorEl)

  return (
    <>
      <IconButton
        size={size}
        onClick={handleClick}
        sx={{
          color: 'text.secondary',
          p: 0.25,
          '&:hover': { color: 'primary.main', bgcolor: 'action.hover' },
        }}
        aria-label={t('help.ariaHelp', { title: content.title })}
      >
        <HelpOutlineIcon fontSize={size === 'small' ? 'small' : 'medium'} />
      </IconButton>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        slotProps={{ paper: { sx: { maxWidth: 440, p: 2 } } }}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            {content.title}
          </Typography>
          <Typography variant="body2" paragraph>
            <strong>{t('help.what')}</strong> {content.what}
          </Typography>
          <Typography variant="body2" paragraph>
            <strong>{t('help.whyImportant')}</strong> {content.whyImportant}
          </Typography>
          {content.whyBad && (
            <Typography variant="body2" paragraph sx={{ color: 'error.main' }}>
              <strong>{t('help.whyBad')}</strong> {content.whyBad}
            </Typography>
          )}
          {content.tips && (
            <Typography variant="body2" color="text.secondary">
              <strong>{t('help.tip')}</strong> {content.tips}
            </Typography>
          )}
        </Box>
      </Popover>
    </>
  )
}

export default HelpTooltip
