library ieee;
use ieee.std_logic_1164.all;

entity kontroller is
        port(clk,res_n: in std_logic;------------------------------------------------oscillitor
             key_color: in std_logic_vector(1 downto 0);----------------------------input
             key_change : in std_logic;
             equal:        in  std_logic;-------------------------------------------zaehlereinheit
             rnd_0,rnd_1:       in std_logic;--------------------------------------random
             expired:            in std_logic;----------------------------------------zeitgeber


            led_on,all_on: out std_logic;--------------------------------------------output
            color: out std_logic_vector(1 downto 0);
            res_step:  out  std_logic;-----------------------------------------------zaehlereinheit
            inc_step:  out  std_logic;
            res_score:  out std_logic;
            inc_score:  out  std_logic;
            next_rn,restore,store:  out  std_logic;-----------------------------------random

            start:                   out std_logic;-----------------------------------zeitgeber
            dec_duration:             out std_logic;
            res_duration:              out std_logic);


end entity kontroller;

architecture behav of kontroller  is

type  state_t is (IDLE,start_wert,re_store_1,
                       led_off_1,led_on_1,next_bit_1,
                              re_store_2,
                                 wait_for_input,led_on_3,led_off_3,
                                        next_bit_2, 
                                    led_on_2,next_level);


signal current_state,next_state: state_t;

begin
        state_vector:process(clk,res_n) is
  begin
       if res_n = '0' then
          current_state <= IDLE;

       else
           if clk'event and clk = '1' then
               current_state <= next_state;
           end if;
       end if;
  end process state_vector;

  state_transition: process(current_state,key_color,key_change,equal,rnd_0,rnd_1,expired) is
  begin
       case current_state is
       when IDLE =>
             if key_change = '1' then
                next_state <= start_wert;
             else
                next_state <= IDLE;
             end if;
       when start_wert =>
             if expired = '1' then
                next_state <= re_store_1;
             else
                next_state <= start_wert;
             end if;
       when re_store_1 => 
    
                next_state <= led_off_1;

       when led_off_1 => 
             if expired = '1' then
                next_state <= led_on_1;
             else
                next_state <= led_off_1;
             end if;
       when led_on_1 =>
             if expired = '1' and equal = '1' then
                next_state <= re_store_2;
             elsif expired = '1' and equal = '0' then
                next_state <= next_bit_1;
             else
                next_state <= led_on_1;
             end if;
       when next_bit_1 =>
             
                next_state <= led_off_1;

       when re_store_2 =>
           
                next_state <= wait_for_input;
            
       when wait_for_input => 
            if key_change = '1' and expired = '0' then
                next_state <= led_on_3;
            elsif expired = '1' and key_change = '0' then
                next_state <= led_on_2;
            else   
                next_state <= wait_for_input;
             end if;
       when  led_on_3 => 
            if key_color /= rnd_1 & rnd_0 and expired = '1' then
                next_state <= led_off_3;
            elsif equal = '0' and expired = '1' then
                next_state <= next_bit_2;
            elsif equal = '1' and expired = '1' then
                next_state <= next_level;
            else 
                next_state <= led_on_3;
             end if;         
       when led_off_3 =>
             if expired = '1'  then
                next_state <= led_on_2;
             else
                next_state <= led_off_3;
             end if;                     
       when next_bit_2 => 
           
                next_state <= wait_for_input;
             
       when next_level => 
           
                next_state <= re_store_1;
       when led_on_2 =>
             if expired = '1'  then
                next_state <= IDLE;
             else
                next_state <= led_on_2;
             end if; 
       end case;                              
  end process state_transition;

  output_vector: process(current_state) is 
  begin
       case current_state is
       when IDLE  => led_on <= '0';
                     all_on <= '0';
                     color  <= "00"; ----------------
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '1';
                     inc_score <=   '0';
                     next_rn  <= '1';
                     restore <= '0';
                     store  <= '0';
                     start <= '0';                  
                     dec_duration <= '0';            
                     res_duration <= '1';
           
      when start_wert  => led_on <= '1';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '1';
                     start <= '1';                  
                     dec_duration <= '0';            
                     res_duration <= '0';


      when  re_store_1  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '1';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '1';
                     store  <= '0';
                     start <= '0';                  
                     dec_duration <= '0';            
                     res_duration <= '0';

when  led_off_1  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '0';
                     start <= '1';                  
                     dec_duration <= '0';            
                     res_duration <= '0';

when  led_on_1  => led_on <= '1';
                     all_on <= '0';
                     color  <= rnd_1 & rnd_0 ; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '0';
                     start <= '1';                  
                     dec_duration <= '0';            
                     res_duration <= '0';
 
when  next_bit_1  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '1';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '1';
                     restore <= '0';
                     store  <= '0';
                     start <= '0';                  
                     dec_duration <= '0';            
                     res_duration <= '0';
 
when  re_store_2  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '1';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '1';
                     store  <= '0';
                     start <= '0';                  
                     dec_duration <= '0';            
                     res_duration <= '0';

when  wait_for_input  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '0';
                     start <= '0';                  
                     dec_duration <= '0';            
                     res_duration <= '0';

when  led_on_3  => led_on <= '1';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '0';
                     start <= '1';                  
                     dec_duration <= '0';            
                     res_duration <= '0'; 

when  led_off_3  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '0';
                     start <= '1';                  
                     dec_duration <= '0';            
                     res_duration <= '0';

when  next_level  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '1';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '0';
                     start <= '0';                  
                     dec_duration <= '1';            
                     res_duration <= '0';

when  led_on_2  => led_on <= '0';
                     all_on <= '1';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '0';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '0';
                     restore <= '0';
                     store  <= '0';
                     start <= '1';                  
                     dec_duration <= '0';            
                     res_duration <= '0';

when  next_bit_2  => led_on <= '0';
                     all_on <= '0';
                     color  <= key_color; 
                     res_step <= '0';  
                     inc_step  <=  '1';
                     res_score <=  '0';
                     inc_score <=   '0';
                     next_rn  <= '1';
                     restore <= '0';
                     store  <= '0';
                     start <= '0';                  
                     dec_duration <= '0';            
                     res_duration <= '0';

       end case;                             
       
  end process output_vector;
       
end architecture behav;
