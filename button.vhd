library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity button is 
   port(clk,res_n: in std_logic;
        tx_n     : in std_logic;
        key_change      : out std_logic);
end entity button;

architecture behav of button is

type  state_t is (IDLE,IS_ONE,HOLD);


signal current_state,next_state: state_t;
signal change_1:std_logic;
signal change_2:std_logic;
--signal key_change:std_logic;

begin

  transition_1: process(clk,res_n) is
  begin
      if res_n = '0' then 
         change_1 <= '1';
         --key <= '0';
      else 
          if clk'event and clk = '1' then
              change_1 <= tx_n;           ----------flip-flop1
          end if;
      end if;
  end process transition_1;

  transition_2: process(clk,res_n) is 
  begin
       if res_n = '0' then
          change_2 <= '0';
         --  key <= '0';
       else 
          if clk'event and clk = '1' then
             change_2 <= not change_1;   ----------flip-flop2

          end if;
       end if;
   end process transition_2;

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

  state_transition: process(current_state,change_2) is
  begin
       case current_state is
       when IDLE =>
             if change_2 = '1' then
                next_state <= IS_ONE;
             else
                next_state <= IDLE;
             end if;
       when IS_ONE =>
             if change_2 = '1' then
                next_state <= HOLD;
             else
                next_state <= IDLE;
             end if;
       when HOLD =>
             if change_2 = '1' then
                next_state <= HOLD;
             else
                next_state <= IDLE;
             end if;
       end case;                              
  end process state_transition;

  output_vector: process(current_state) is 
  begin
       case current_state is
       when IDLE | HOLD => key_change <= '0';
       when IS_one => key_change  <= '1';
                   
       end case;                             
       
  end process output_vector;
       
end architecture behav;
    







 

   