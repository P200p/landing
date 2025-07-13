// commands/loan.ts
import { SlashCommandBuilder } from 'discord.js'
import { supabase } from '../supabaseClient'

export const data = new SlashCommandBuilder()
  .setName('ปล่อยกู้')
  .setDescription('ปล่อยกู้ให้ user คนแรกที่กด')
  .addIntegerOption(opt => opt.setName('จำนวน').setDescription('จำนวนเครดิต'))

export async function execute(interaction) {
  const amount = interaction.options.getInteger('จำนวน')
  const button = new ButtonBuilder().setCustomId('request-loan').setLabel('ขอกู้เงิน').setStyle(ButtonStyle.Primary)
  
  const row = new ActionRowBuilder<ButtonBuilder>().addComponents(button)
  
  await interaction.reply({
    content: `ปล่อยกู้ด่วน! ${amount} เครดิต คนแรกที่กดจะได้สิทธิ์ทันที!`,
    components: [row]
  })

  // รอ event สำหรับการกดปุ่มจาก user
}
import { ButtonBuilder, ButtonStyle, ActionRowBuilder } from 'discord.js'